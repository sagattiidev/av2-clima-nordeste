"""
Módulo compartilhado: conexão com o Postgres da Aiven e leitura da API de
dados abertos Open-Meteo (clima). Usado por app.py, producer.py e consumer.py,
para não duplicar a lógica de acesso a dados em cada script.

Fonte dos dados: https://open-meteo.com/ — API pública e gratuita para uso não
comercial, sem chave de acesso. Os valores diários dos dias passados vêm de
modelos meteorológicos (reanálise), não de uma estação física específica.
"""

import datetime
import json
import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import psycopg2
import requests
from psycopg2 import errors as pg_errors
from psycopg2 import pool as psycopg2_pool
from psycopg2.extras import RealDictCursor, execute_values

DB_URL = os.environ.get("AIVEN_DB_URL")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Capitais do Nordeste monitoradas (latitude/longitude do centro da cidade).
CIDADES = {
    "salvador": {"nome": "Salvador (BA)", "lat": -12.9714, "lon": -38.5014},
    "recife": {"nome": "Recife (PE)", "lat": -8.0476, "lon": -34.8770},
    "fortaleza": {"nome": "Fortaleza (CE)", "lat": -3.7319, "lon": -38.5267},
    "natal": {"nome": "Natal (RN)", "lat": -5.7945, "lon": -35.2110},
    "sao-luis": {"nome": "São Luís (MA)", "lat": -2.5307, "lon": -44.3068},
}
CIDADE_PADRAO = "salvador"

# Variáveis diárias pedidas à API (o nome da chave é o nome oficial da Open-Meteo).
VARIAVEIS = {
    "temperature_2m_max": {"nome": "Temperatura máxima", "unidade": "°C", "casas": 1},
    "temperature_2m_min": {"nome": "Temperatura mínima", "unidade": "°C", "casas": 1},
    "precipitation_sum": {"nome": "Chuva acumulada no dia", "unidade": "mm", "casas": 1},
}
DIAS_HISTORICO = 30
MAX_PAST_DAYS = 92  # limite da Open-Meteo para `past_days`

# Pool de conexões: a Aiven fica em outra região/rede que o Render, então abrir
# uma conexão nova (TCP + handshake SSL) custa ~1s toda vez. Com o pool, as
# conexões são abertas uma vez e reaproveitadas entre requisições.
_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        if not DB_URL:
            raise RuntimeError("AIVEN_DB_URL não configurada")
        _pool = psycopg2_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=DB_URL,
            sslmode="require",
            cursor_factory=RealDictCursor,
            connect_timeout=10,
        )
    return _pool


@contextmanager
def get_connection():
    """Empresta uma conexão do pool e a devolve ao sair do bloco `with`."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        # Uma leitura SELECT também inicia uma transação no psycopg2.
        # Encerrá-la evita conexões "idle in transaction" no pool.
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def init_db():
    """Cria as tabelas caso ainda não existam.

    Vários workers do gunicorn podem chamar esta função quase ao mesmo tempo;
    `CREATE TABLE IF NOT EXISTS` não é 100% atômico entre transações
    concorrentes, então ignoramos o erro inofensivo de "tabela já criada".
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clima_diario (
                        city       TEXT NOT NULL,
                        variable   TEXT NOT NULL,
                        ref_date   DATE NOT NULL,
                        value      NUMERIC NOT NULL,
                        fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        PRIMARY KEY (city, variable, ref_date)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS visits (
                        id SERIAL PRIMARY KEY,
                        path TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
            conn.commit()
    except pg_errors.DuplicateTable:
        pass
    except psycopg2.errors.UniqueViolation as exc:
        if "pg_type" not in str(exc):
            raise


# --------------------------------------------------------------------------
# API Open-Meteo
# --------------------------------------------------------------------------
def parse_openmeteo(payload, days):
    """Converte o JSON da Open-Meteo em uma lista de dias, do mais antigo ao mais novo.

    Cada item: {"ref_date": date, "values": {variavel: float}}. Valores nulos
    (a API devolve null quando não há dado) são omitidos; dias sem nenhum valor
    são descartados. Levanta ValueError se a resposta não tiver o formato esperado.
    """
    daily = payload.get("daily") if isinstance(payload, dict) else None
    if not isinstance(daily, dict) or not daily.get("time"):
        raise ValueError("Resposta da Open-Meteo sem o bloco 'daily'")
    dias = []
    for i, raw_date in enumerate(daily["time"]):
        values = {}
        for var in VARIAVEIS:
            serie = daily.get(var) or []
            if i < len(serie) and serie[i] is not None:
                values[var] = float(serie[i])
        if values:
            dias.append({"ref_date": datetime.date.fromisoformat(raw_date), "values": values})
    return dias[-days:] if days > 0 else dias


def fetch_city(city_key, days=DIAS_HISTORICO):
    """Busca os últimos `days` dias de uma cidade na Open-Meteo."""
    cidade = CIDADES[city_key]
    params = {
        "latitude": cidade["lat"],
        "longitude": cidade["lon"],
        "daily": ",".join(VARIAVEIS),
        "past_days": max(1, min(days, MAX_PAST_DAYS)),
        "forecast_days": 1,
        "timezone": "auto",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    resp.raise_for_status()
    return parse_openmeteo(resp.json(), days)


# --------------------------------------------------------------------------
# Persistência
# --------------------------------------------------------------------------
def upsert_days(city_key, dias):
    """Grava (ou atualiza) dias de uma cidade com UMA instrução SQL em lote.

    Usado pelo cache do app.py e pelo consumer.py do Kafka.
    """
    rows = [
        (city_key, var, d["ref_date"], value)
        for d in dias
        for var, value in d["values"].items()
    ]
    if not rows:
        return 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO clima_diario (city, variable, ref_date, value, fetched_at)
                VALUES %s
                ON CONFLICT (city, variable, ref_date)
                DO UPDATE SET value = EXCLUDED.value, fetched_at = now();
                """,
                rows,
                template="(%s, %s, %s, %s, now())",
            )
        conn.commit()
    return len(rows)


def last_fetch(city_key):
    """Momento da última atualização dos dados de uma cidade (ou None)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(fetched_at) AS last_fetch FROM clima_diario WHERE city = %s;",
                (city_key,),
            )
            row = cur.fetchone()
    return row["last_fetch"] if row else None


def pivot_rows(rows):
    """Agrupa linhas (ref_date, variable, value) em dias, do mais antigo ao mais novo."""
    por_dia = {}
    for r in rows:
        por_dia.setdefault(r["ref_date"], {})[r["variable"]] = float(r["value"])
    return [{"ref_date": d, "values": por_dia[d]} for d in sorted(por_dia)]


@lru_cache(maxsize=1)
def _historico_inicial():
    """Leitura da série histórica distribuída com a aplicação."""
    arquivo = Path(__file__).with_name("historico_open_meteo.json")
    return json.loads(arquivo.read_text(encoding="utf-8"))["cities"]


def get_history(city_key, days=DIAS_HISTORICO):
    """Lê o histórico do banco e usa a série local quando ele está vazio."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ref_date, variable, value
                FROM clima_diario
                WHERE city = %s
                ORDER BY ref_date DESC
                LIMIT %s;
                """,
                (city_key, days * len(VARIAVEIS)),
            )
            rows = cur.fetchall()
    if rows:
        return pivot_rows(rows)[-days:]
    dados = _historico_inicial().get(city_key)
    if dados is None:
        return []
    historico = parse_openmeteo({"daily": dados}, days)
    return [dict(dia, historico_local=True) for dia in historico]


def log_visit(path):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO visits (path) VALUES (%s);", (path,))
        conn.commit()


def count_visits():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM visits;")
            return cur.fetchone()["total"]


# --------------------------------------------------------------------------
# Registro de acessos (checkpoint 10 do roteiro de laboratório)
# --------------------------------------------------------------------------
def get_visits_per_minute(minutes=60):
    """Contagens de acessos agrupadas por minuto (horário UTC)."""
    minutes = max(1, min(1440, int(minutes)))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date_trunc('minute', created_at) AS bucket,
                       COUNT(*) AS total
                FROM visits
                WHERE created_at >= now() - (%s * interval '1 minute')
                GROUP BY bucket ORDER BY bucket;
                """,
                (minutes,),
            )
            rows = cur.fetchall()
    return [
        {"minuto": row["bucket"].astimezone(datetime.timezone.utc).strftime("%H:%M"),
         "total": int(row["total"])}
        for row in rows
    ]


def get_recent_visits(limit=10):
    """Últimos acessos para conferência de persistência no PostgreSQL."""
    limit = max(1, min(50, int(limit)))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT path, created_at
                FROM visits ORDER BY created_at DESC LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()
    return [
        {"rota": row["path"],
         "data_hora_utc": row["created_at"].astimezone(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M:%S")}
        for row in rows
    ]

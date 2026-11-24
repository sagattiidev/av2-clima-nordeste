"""
Painel Clima do Nordeste — App Flask
Lê os dados diários de clima (temperatura e chuva) das capitais do Nordeste do
Postgres da Aiven (tabela clima_diario). Os dados chegam lá de duas formas, que
podem conviver:

  1. Cache em lote: este próprio app busca dados novos na API aberta Open-Meteo
     quando o cache está velho (ver refresh_stale_cities) — funciona sozinho,
     sem depender de Kafka.
  2. Streaming: producer.py publica no Kafka, consumer.py assina o tópico e
     grava aqui — ver README para a arquitetura completa.

Variáveis de ambiente esperadas (ver .env.example):
  AIVEN_DB_URL   -> string de conexão fornecida pela Aiven
  PORT           -> porta HTTP (default 8080)
  CACHE_HOURS    -> horas antes de buscar dados novos na API (default 6)
"""

import datetime
import os
import time

import requests
from flask import Flask, jsonify, render_template, request

import clima_client as clima

app = Flask(__name__)

CACHE_HOURS = int(os.environ.get("CACHE_HOURS", 6))
START_TIME = time.time()
PAUSA_OPEN_METEO_SEGUNDOS = 300
_proxima_consulta_open_meteo = 0.0
DIA_CHUVOSO_MM = 1.0  # a partir de 1 mm no dia contamos como "dia com chuva"

# Garante que as tabelas existam assim que o módulo é carregado — necessário
# porque em produção o app roda via gunicorn (`gunicorn app:app`), que nunca
# executa o bloco `if __name__ == "__main__":` lá embaixo.
clima.init_db()


def is_cache_stale(city_key):
    ultimo = clima.last_fetch(city_key)
    if not ultimo:
        return True
    idade = datetime.datetime.now(datetime.timezone.utc) - ultimo
    return idade > datetime.timedelta(hours=CACHE_HOURS)


def refresh_city(city_key):
    dias = clima.fetch_city(city_key)
    clima.upsert_days(city_key, dias)


def refresh_stale_cities():
    """Só busca na Open-Meteo se ninguém (nem o consumer do Kafka) já
    atualizou a cidade recentemente. Se a API estiver fora do ar, o app não
    quebra: segue servindo o que já está no banco."""
    global _proxima_consulta_open_meteo
    if time.monotonic() < _proxima_consulta_open_meteo:
        return

    for city_key in clima.CIDADES:
        if is_cache_stale(city_key):
            try:
                refresh_city(city_key)
            except (requests.RequestException, ValueError, KeyError) as exc:
                app.logger.warning("Falha ao atualizar %s: %s", city_key, exc)
                response = getattr(exc, "response", None)
                if response is not None and response.status_code == 429:
                    _proxima_consulta_open_meteo = time.monotonic() + PAUSA_OPEN_METEO_SEGUNDOS
                    return


def _valor(dia, variavel):
    return dia["values"].get(variavel) if dia else None


def _soma(historico, variavel, ultimos):
    return round(sum(d["values"].get(variavel, 0.0) for d in historico[-ultimos:]), 1)


def resumir_cidade(city_key, historico):
    """Indicadores de uma cidade a partir do histórico (lista de dias)."""
    ultimo = historico[-1] if historico else None
    anterior = historico[-2] if len(historico) > 1 else None
    tmax, tmax_ant = _valor(ultimo, "temperature_2m_max"), _valor(anterior, "temperature_2m_max")
    delta = round(tmax - tmax_ant, 1) if tmax is not None and tmax_ant is not None else None
    maximas = [d["values"]["temperature_2m_max"] for d in historico if "temperature_2m_max" in d["values"]]
    minimas = [d["values"]["temperature_2m_min"] for d in historico if "temperature_2m_min" in d["values"]]
    return {
        "key": city_key,
        "nome": clima.CIDADES[city_key]["nome"],
        "data": ultimo["ref_date"].strftime("%d/%m/%Y") if ultimo else None,
        "tmax": tmax,
        "tmin": _valor(ultimo, "temperature_2m_min"),
        "chuva_dia": _valor(ultimo, "precipitation_sum"),
        "delta_tmax": delta,
        "chuva_7d": _soma(historico, "precipitation_sum", 7),
        "chuva_30d": _soma(historico, "precipitation_sum", 30),
        "dias_chuvosos": sum(
            1 for d in historico if d["values"].get("precipitation_sum", 0.0) >= DIA_CHUVOSO_MM
        ),
        "maior_tmax": max(maximas) if maximas else None,
        "menor_tmin": min(minimas) if minimas else None,
        "dias": len(historico),
        "historico_local": bool(ultimo and ultimo.get("historico_local")),
    }


def get_dashboard_data(city_key):
    refresh_stale_cities()

    historicos = {key: clima.get_history(key) for key in clima.CIDADES}
    ranking = [resumir_cidade(key, historicos[key]) for key in clima.CIDADES]
    atual = next(c for c in ranking if c["key"] == city_key)
    historico = historicos[city_key]

    com_dados = [c for c in ranking if c["tmax"] is not None]
    mais_quente = max(com_dados, key=lambda c: c["tmax"])["key"] if com_dados else None
    mais_chuvosa = max(ranking, key=lambda c: c["chuva_30d"])["key"] if com_dados else None

    return {
        "cidade": atual,
        "cidades": [{"key": k, "nome": v["nome"]} for k, v in clima.CIDADES.items()],
        "ranking": ranking,
        "mais_quente": mais_quente,
        "mais_chuvosa": mais_chuvosa,
        "labels": [d["ref_date"].strftime("%d/%m") for d in historico],
        "tmax": [d["values"].get("temperature_2m_max") for d in historico],
        "tmin": [d["values"].get("temperature_2m_min") for d in historico],
        "chuva": [d["values"].get("precipitation_sum") for d in historico],
        "total_visits": clima.count_visits(),
        "visits_per_minute": clima.get_visits_per_minute(),
        "recent_visits": clima.get_recent_visits(),
        "uptime_seconds": int(time.time() - START_TIME),
        "server_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cache_hours": CACHE_HOURS,
    }


def cidade_da_requisicao():
    """Cidade escolhida em ?cidade=...; valor desconhecido cai na cidade padrão."""
    escolhida = request.args.get("cidade", clima.CIDADE_PADRAO)
    return escolhida if escolhida in clima.CIDADES else clima.CIDADE_PADRAO


@app.route("/")
def dashboard():
    clima.log_visit("/")
    return render_template("dashboard.html", data=get_dashboard_data(cidade_da_requisicao()))


@app.route("/api/clima")
def api_clima():
    clima.log_visit("/api/clima")
    return jsonify(get_dashboard_data(cidade_da_requisicao()))


@app.route("/api/visitas")
def api_visitas():
    """Estatísticas de acessos persistidas no Aiven; usadas no painel a cada 10 s."""
    result = jsonify({
        "status": "ok",
        "total_visits": clima.count_visits(),
        "visits_per_minute": clima.get_visits_per_minute(),
        "recent_visits": clima.get_recent_visits(),
    })
    result.headers["Cache-Control"] = "no-store"
    return result


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Força a atualização de todas as cidades, ignorando a idade do cache."""
    for city_key in clima.CIDADES:
        try:
            refresh_city(city_key)
        except (requests.RequestException, ValueError, KeyError) as exc:
            return jsonify({"status": "error", "cidade": city_key, "detail": str(exc)}), 502
    return jsonify({"status": "ok", "refreshed": list(clima.CIDADES)})


@app.route("/healthz")
def healthz():
    """Usado pelo pipeline de CI/CD e pela plataforma de deploy (health check)."""
    try:
        with clima.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return jsonify({"status": "ok"}), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "error", "detail": str(exc)}), 503


if __name__ == "__main__":
    refresh_stale_cities()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

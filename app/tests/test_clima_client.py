"""Testes de clima_client: parsing da Open-Meteo e agrupamento — sem rede e sem banco."""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import clima_client as clima  # noqa: E402


def payload(n=3):
    base = datetime.date(2026, 11, 20)
    return {
        "daily": {
            "time": [(base + datetime.timedelta(days=i)).isoformat() for i in range(n)],
            "temperature_2m_max": [30.1 + i for i in range(n)],
            "temperature_2m_min": [24.0 + i for i in range(n)],
            "precipitation_sum": [0.0, None, 12.4][:n],
        }
    }


def test_parse_converte_dias_e_omite_nulos():
    dias = clima.parse_openmeteo(payload(), days=30)
    assert [d["ref_date"] for d in dias] == [
        datetime.date(2026, 11, 20), datetime.date(2026, 11, 21), datetime.date(2026, 11, 22),
    ]
    assert dias[0]["values"]["precipitation_sum"] == 0.0
    assert "precipitation_sum" not in dias[1]["values"]  # null não vira zero
    assert dias[2]["values"]["temperature_2m_max"] == 32.1


def test_parse_recorta_os_ultimos_dias():
    dias = clima.parse_openmeteo(payload(), days=2)
    assert [d["ref_date"].day for d in dias] == [21, 22]


def test_parse_descarta_dia_sem_nenhum_valor():
    p = {"daily": {"time": ["2026-11-20"], "temperature_2m_max": [None],
                   "temperature_2m_min": [None], "precipitation_sum": [None]}}
    assert clima.parse_openmeteo(p, days=30) == []


def test_parse_resposta_invalida_levanta_valueerror():
    for ruim in ({}, {"daily": {}}, {"error": True}, None, []):
        try:
            clima.parse_openmeteo(ruim, days=30)
        except ValueError:
            continue
        raise AssertionError(f"não levantou ValueError para {ruim!r}")


def test_pivot_rows_agrupa_por_dia_em_ordem():
    d1, d2 = datetime.date(2026, 11, 21), datetime.date(2026, 11, 20)
    rows = [
        {"ref_date": d1, "variable": "temperature_2m_max", "value": 31},
        {"ref_date": d2, "variable": "temperature_2m_max", "value": 29.5},
        {"ref_date": d1, "variable": "precipitation_sum", "value": "2.5"},
    ]
    dias = clima.pivot_rows(rows)
    assert [d["ref_date"] for d in dias] == [d2, d1]
    assert dias[1]["values"] == {"temperature_2m_max": 31.0, "precipitation_sum": 2.5}


def test_fetch_city_monta_a_requisicao_certa(monkeypatch):
    chamadas = []

    class Resposta:
        def raise_for_status(self):
            pass

        def json(self):
            return payload()

    def falso_get(url, params=None, timeout=None):
        chamadas.append((url, params, timeout))
        return Resposta()

    monkeypatch.setattr(clima.requests, "get", falso_get)
    dias = clima.fetch_city("salvador", days=2)
    url, params, timeout = chamadas[0]
    assert url == clima.OPEN_METEO_URL
    assert params["latitude"] == clima.CIDADES["salvador"]["lat"]
    assert params["daily"] == "temperature_2m_max,temperature_2m_min,precipitation_sum"
    assert params["past_days"] == 2 and params["forecast_days"] == 1
    assert timeout == 10
    assert len(dias) == 2


def test_fetch_city_limita_past_days_ao_maximo_da_api(monkeypatch):
    vistos = []

    class Resposta:
        def raise_for_status(self):
            pass

        def json(self):
            return payload()

    monkeypatch.setattr(clima.requests, "get",
                        lambda url, params=None, timeout=None: vistos.append(params) or Resposta())
    clima.fetch_city("recife", days=500)
    assert vistos[0]["past_days"] == clima.MAX_PAST_DAYS


def test_cidades_tem_coordenadas_validas():
    assert clima.CIDADE_PADRAO in clima.CIDADES
    for chave, c in clima.CIDADES.items():
        assert -90 <= c["lat"] <= 90 and -180 <= c["lon"] <= 180, chave
        assert c["nome"]


def test_visits_per_minute_consulta_postgres(monkeypatch):
    from contextlib import contextmanager
    import datetime

    class Cursor:
        def execute(self, sql, params):
            assert "date_trunc('minute'" in sql
            assert params == (60,)

        def fetchall(self):
            return [{"bucket": datetime.datetime(2026, 11, 24, 21, 30, tzinfo=datetime.timezone.utc),
                     "total": 4}]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

    @contextmanager
    def fake_conn():
        yield Connection()

    monkeypatch.setattr(clima, "get_connection", fake_conn)
    assert clima.get_visits_per_minute() == [{"minuto": "21:30", "total": 4}]


def test_recent_visits_limita_consulta(monkeypatch):
    from contextlib import contextmanager
    import datetime

    class Cursor:
        def execute(self, sql, params):
            assert "FROM visits" in sql and params == (50,)

        def fetchall(self):
            return [{"path": "/api/clima", "created_at":
                     datetime.datetime(2026, 11, 24, 21, 31, tzinfo=datetime.timezone.utc)}]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

    @contextmanager
    def fake_conn():
        yield Connection()

    monkeypatch.setattr(clima, "get_connection", fake_conn)
    result = clima.get_recent_visits(999)
    assert result == [{"rota": "/api/clima", "data_hora_utc": "24/11/2026 21:31:00"}]

"""Testes das rotas Flask com o acesso ao banco e à API substituídos por dados falsos."""

import datetime
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import clima_client as clima  # noqa: E402
import requests  # noqa: E402


def historico_falso(base_tmax):
    hoje = datetime.date(2026, 11, 24)
    dias = []
    for i in range(3):
        dias.append({
            "ref_date": hoje - datetime.timedelta(days=2 - i),
            "values": {
                "temperature_2m_max": base_tmax + i,
                "temperature_2m_min": base_tmax - 6,
                "precipitation_sum": [0.0, 3.0, 5.5][i],
            },
        })
    return dias


def carregar_app(monkeypatch, ultimo=None):
    """Importa app.py com banco e API falsos (init_db roda no import do módulo)."""
    agora = ultimo or datetime.datetime.now(datetime.timezone.utc)
    monkeypatch.setattr(clima, "init_db", lambda: None)
    monkeypatch.setattr(clima, "last_fetch", lambda city: agora)
    base = {"salvador": 30.0, "recife": 31.0, "fortaleza": 33.0, "natal": 29.0, "sao-luis": 32.0}
    monkeypatch.setattr(clima, "get_history", lambda city, days=30: historico_falso(base[city]))
    monkeypatch.setattr(clima, "log_visit", lambda path: None)
    monkeypatch.setattr(clima, "count_visits", lambda: 7)
    monkeypatch.setattr(clima, "get_visits_per_minute", lambda minutes=60: [
        {"minuto": "21:30", "total": 2}, {"minuto": "21:31", "total": 5}
    ])
    monkeypatch.setattr(clima, "get_recent_visits", lambda limit=10: [
        {"data_hora_utc": "24/11/2026 21:31:00", "rota": "/"}
    ])
    module = importlib.import_module("app")
    return importlib.reload(module)


def test_dashboard_renderiza_cidade_padrao_e_selos(monkeypatch):
    modulo = carregar_app(monkeypatch)
    html = modulo.app.test_client().get("/").get_data(as_text=True)
    assert "Clima do Nordeste" in html
    assert "Salvador (BA)" in html
    assert 'aria-current="page"' in html
    assert "mais quente" in html and "mais chuvosa" in html


def test_cidade_desconhecida_cai_na_padrao(monkeypatch):
    modulo = carregar_app(monkeypatch)
    resposta = modulo.app.test_client().get("/api/clima?cidade=atlantida")
    assert resposta.status_code == 200
    assert resposta.get_json()["cidade"]["key"] == "salvador"


def test_api_clima_traz_indicadores_corretos(monkeypatch):
    modulo = carregar_app(monkeypatch)
    dados = modulo.app.test_client().get("/api/clima?cidade=fortaleza").get_json()
    cidade = dados["cidade"]
    assert cidade["nome"] == "Fortaleza (CE)"
    assert cidade["tmax"] == 35.0 and cidade["delta_tmax"] == 1.0
    assert cidade["chuva_30d"] == 8.5 and cidade["dias_chuvosos"] == 2
    assert dados["mais_quente"] == "fortaleza"
    assert dados["labels"] == ["22/11", "23/11", "24/11"]
    assert dados["total_visits"] == 7


def test_cache_velho_ou_vazio_e_detectado(monkeypatch):
    modulo = carregar_app(monkeypatch)
    monkeypatch.setattr(clima, "last_fetch", lambda city: None)
    assert modulo.is_cache_stale("salvador") is True
    velho = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=modulo.CACHE_HOURS + 1)
    monkeypatch.setattr(clima, "last_fetch", lambda city: velho)
    assert modulo.is_cache_stale("salvador") is True
    novo = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
    monkeypatch.setattr(clima, "last_fetch", lambda city: novo)
    assert modulo.is_cache_stale("salvador") is False


def test_api_fora_do_ar_nao_derruba_o_painel(monkeypatch):
    velho = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
    modulo = carregar_app(monkeypatch, ultimo=velho)

    def falha(city, days=30):
        raise requests.ConnectionError("sem internet")

    monkeypatch.setattr(clima, "fetch_city", falha)
    resposta = modulo.app.test_client().get("/")
    assert resposta.status_code == 200  # segue servindo o cache do banco


def test_refresh_ok_e_erro_502(monkeypatch):
    modulo = carregar_app(monkeypatch)
    gravados = []
    monkeypatch.setattr(clima, "fetch_city", lambda city, days=30: historico_falso(30.0))
    monkeypatch.setattr(clima, "upsert_days", lambda city, dias: gravados.append(city) or 3)
    cliente = modulo.app.test_client()
    ok = cliente.post("/api/refresh")
    assert ok.status_code == 200 and ok.get_json()["status"] == "ok"
    assert gravados == list(clima.CIDADES)

    def falha(city, days=30):
        raise requests.Timeout("lento")

    monkeypatch.setattr(clima, "fetch_city", falha)
    erro = cliente.post("/api/refresh")
    assert erro.status_code == 502 and erro.get_json()["status"] == "error"


def test_healthz_503_quando_banco_cai(monkeypatch):
    modulo = carregar_app(monkeypatch)

    def sem_banco():
        raise RuntimeError("banco fora")

    monkeypatch.setattr(clima, "get_connection", sem_banco)
    resposta = modulo.app.test_client().get("/healthz")
    assert resposta.status_code == 503 and resposta.get_json()["status"] == "error"


def test_resumo_de_cidade_sem_dados(monkeypatch):
    modulo = carregar_app(monkeypatch)
    resumo = modulo.resumir_cidade("natal", [])
    assert resumo["tmax"] is None and resumo["chuva_30d"] == 0 and resumo["dias"] == 0


def test_dashboard_mostra_grafico_e_tabela_de_acessos(monkeypatch):
    modulo = carregar_app(monkeypatch)
    html = modulo.app.test_client().get("/").get_data(as_text=True)
    assert 'id="visitsChart"' in html
    assert "Visitas por minuto" in html
    assert "Últimos acessos" in html
    assert "24/11/2026 21:31:00" in html
    assert "POST /api/refresh" not in html


def test_dashboard_mostra_aviso_de_refresh_quando_faltam_dados(monkeypatch):
    modulo = carregar_app(monkeypatch)
    monkeypatch.setattr(clima, "get_history", lambda city, days=30: [])
    html = modulo.app.test_client().get("/").get_data(as_text=True)
    assert "POST /api/refresh" in html


def test_api_clima_devolve_metricas_de_trafego(monkeypatch):
    modulo = carregar_app(monkeypatch)
    response = modulo.app.test_client().get("/api/clima")
    assert response.status_code == 200
    assert response.get_json()["visits_per_minute"][1]["total"] == 5
    assert response.get_json()["recent_visits"][0]["rota"] == "/"


def test_endpoint_visitas_mostra_metricas_em_tempo_real(monkeypatch):
    modulo = carregar_app(monkeypatch)
    resposta = modulo.app.test_client().get("/api/visitas")
    assert resposta.status_code == 200
    assert resposta.headers["Cache-Control"] == "no-store"
    assert resposta.get_json()["total_visits"] == 7
    assert resposta.get_json()["visits_per_minute"][0]["minuto"] == "21:30"

# Clima do Nordeste

AV2 de Miqueias Souza dos Santos, baseada no projeto de DevOps fornecido na disciplina.

## Painel

O painel usa dados da Open-Meteo para mostrar temperaturas máximas e mínimas e volume de chuva em Salvador, Recife, Fortaleza, Natal e São Luís. Os dados ficam em cache no PostgreSQL. A interface permite selecionar uma cidade e comparar os indicadores entre as capitais.

O painel também mostra o total de visitas, um gráfico de acessos por minuto e uma tabela com os últimos acessos. Essas métricas são consultadas a cada 10 segundos.

Quando o PostgreSQL ainda não tem dados de uma cidade, o painel usa a série da Open-Meteo de 25/10 a 23/11/2026 incluída no projeto e exibe a data de referência. Assim que a primeira atualização chega ao banco, o painel passa a usar os registros do PostgreSQL. Se a Open-Meteo retornar HTTP 429, as consultas automáticas aguardam cinco minutos antes de tentar novamente.

[Documentação da Open-Meteo](https://open-meteo.com/en/docs)

## 2. Estrutura principal

```text
app/
  Dockerfile                 # Render: Root Directory = app
  .dockerignore
  app.py                     # Flask: dashboard, APIs, monitoramento de acesso
  clima_client.py            # Open-Meteo + consultas ao PostgreSQL
  templates/dashboard.html  # visual, gráficos, tabela
  static/style.css
  tests/                     # 22 testes de funções e rotas
  requirements.txt
  .env.example
terraform/                  # provisionamento Aiven PostgreSQL
.github/workflows/
  infra.yml                  # infraestrutura manual
  ci-cd.yml                  # test -> build-and-push -> deploy
  refresh-data.yml          # atualização agendada
  kafka-*.yml               # opcionais, manuais
REGISTRO_DE_EVENTOS.md
CHECKLIST_DO_LABORATORIO.md
RELATORIO_TECNICO_MIQUEIAS.pdf
```

## 3. Passo a passo do roteiro da atividade

1. **Aiven:** faça cadastro, crie um projeto e anote o nome exato (`AIVEN_PROJECT`).
2. **Token:** em Profile → Authentication tokens, gere `AIVEN_API_TOKEN`; **não coloque o token no ZIP ou no relatório**.
3. **GitHub:** crie um repositório próprio, envie todos os arquivos **incluindo pastas ocultas** `.github/workflows`. Verifique os workflows em Actions.
4. **Secrets:** em Settings → Secrets and variables → Actions, cadastre **`AIVEN_API_TOKEN`, `AIVEN_PROJECT`, `RENDER_DEPLOY_HOOK_URL`, `APP_HEALTHCHECK_URL`**. Os dois últimos só podem ser preenchidos definitivamente após criar o serviço no Render. Nunca grave seus valores no repositório.
5. **PostgreSQL:** execute manualmente em Actions → **Infra - Provisionar Aiven (Terraform)** → Run workflow. Use `validate` para verificar o Terraform, `plan` para conferir a configuração e `apply` em `main` para provisionar o PostgreSQL gratuito. Confirme que o serviço está **Running** e copie a Service URI. O Terraform usa plano `free-1-1gb` por padrão, sujeito à disponibilidade da conta; **confira no Aiven o plano efetivo antes de aprovar a criação**. Não escolha `hobbyist` sem concordar com o preço. O runner do GitHub não guarda o state Terraform entre execuções; para reaplicar com segurança, configure backend remoto ou peça orientação ao professor, em vez de repetir o workflow.
6. **Render:** New → Web Service → Git Provider, escolha o repositório. **Root Directory = `app`**, Runtime = **Docker**, plano **Free**, Auto-Deploy **Off**. O arquivo `render.yaml` também permite importar essa configuração como Blueprint. O Dockerfile está dentro de `app/`, alinhado ao guia.
7. **Ambiente:** no Render, configure **`AIVEN_DB_URL`** com a Service URI Aiven e **`PORT=8080`**. Inicie o deploy e copie a URL pública; configure `APP_HEALTHCHECK_URL` como **URL base sem `/healthz`**, exemplo `https://nome.onrender.com`.
8. **Deploy Hook:** em Render → Settings → Deploy Hook, copie e preencha `RENDER_DEPLOY_HOOK_URL` no GitHub.
9. **CI/CD:** um commit em `main` alterando `app/` ou `.github/workflows/ci-cd.yml` dispara **test → build-and-push → deploy**. Acompanhe os três jobs no Actions. As etapas do Render aguardam os dois secrets. Para habilitar o refresh agendado após a publicação, defina a variável `ENABLE_RENDER_REFRESH=true` no Actions. O deploy checa `GET /healthz` no Render; espere pelo serviço sair de cold start.
10. **Validar:** acesse a URL pública algumas vezes. Confira os cinco indicadores climáticos, **total de visitas**, **gráfico por minuto**, **últimos acessos** e atualização a cada 10 segundos. Confirme `/healthz` respondendo `{"status":"ok"}` apenas com banco acessível.

## 4. Como testar no VS Code antes da publicação

No Windows, no terminal PowerShell, dentro da pasta `app`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt pytest flake8
python -m pytest -q tests
python -m compileall -q .
```

Para abrir o app localmente **com banco Aiven configurado**:

```powershell
$env:AIVEN_DB_URL = "COLE_AQUI_SUA_SERVICE_URI_PRIVADA"
$env:PORT = "8080"
python app.py
```

Abra `http://127.0.0.1:8080/`. Sem `AIVEN_DB_URL` e um banco acessível, o app não inicia — isso é esperado no modo Aiven exigido pelo roteiro. **Nunca grave a URI real em arquivos enviados ao Canvas.**

## 5. API

| Rota | Função |
|---|---|
| `GET /` | Painel com clima e monitoramento de visitas |
| `GET /api/clima?cidade=salvador` | Dados climáticos e do dashboard em JSON |
| `GET /api/visitas` | Métricas de acessos do PostgreSQL, sem registrar visitas extras |
| `POST /api/refresh` | Atualiza o clima com a Open-Meteo |
| `GET /healthz` | Testa conexão com o PostgreSQL para CI/CD |

As consultas ao banco usam parâmetros SQL; a fonte Open-Meteo é acessada via HTTPS com timeout. Os indicadores climáticos são atualizados pela API quando o cache vence; os acessos são atualizados a cada 10 segundos.

## 6. Cuidados e limitações

- Os resultados dos testes e da publicação no GitHub estão em `evidencias/` e no registro de eventos.
- O arquivo `CHECKLIST_DO_LABORATORIO.md` indica cada evidência a anexar.
- Não coloque tokens, senhas, Service URI ou chaves nos prints ou no ZIP.
- Serviços Free variam por conta; Render pode passar por cold start. Aiven e Render mudam os planos; confira antes de criar recursos.
- Kafka e Grafana foram preservados como **opcionais** e não são ativados automaticamente.
- A API Open-Meteo pode falhar ou demorar; nesse caso o app tenta usar o que já está no banco.

## 7. Créditos

- Projeto base de DevOps e portal econômico: material de referência fornecido pelo professor.
- Dados climáticos: Open-Meteo, https://open-meteo.com/.
- Aplicação adaptada para a AV2 de **Miqueias Souza dos Santos**.

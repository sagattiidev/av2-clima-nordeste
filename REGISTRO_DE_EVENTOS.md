# Registro de eventos — AV2 DevOps (Pipeline com Aiven.io)

**Aluno:** Miqueias Souza dos Santos
**Aplicação:** Clima do Nordeste (dados abertos da Open-Meteo)
**Repositório GitHub:** [sagattiidev/av2-clima-nordeste](https://github.com/sagattiidev/av2-clima-nordeste)  
**URL do app no Render:** Pendente

> Preencha cada linha **com o que de fato aconteceu**: data e hora, resultado e o nome do arquivo do print
> na pasta `evidencias/`. Se uma etapa falhou, registre o erro e como resolveu: isso também conta como evidência.

## Etapa 0 — Modificação da aplicação (código)

| Item | Descrição |
|---|---|
| Ponto de partida | Projeto de referência `aiven-devops-pipeline` (painel do Banco Central), fornecido pelo professor |
| Nova fonte de dados | Open-Meteo (temperatura e chuva diárias de Salvador, Recife, Fortaleza, Natal e São Luís) |
| Banco | Tabela `clima_diario` no lugar de `bcb_series`; gravação em lote |
| Aplicação | Novo cliente (`clima_client.py`), seletor de cidade, gráfico barras + linhas, comparativo com selos |
| Pipeline | `pytest` no CI (21 testes definidos); Kafka e Grafana opcionais no Terraform; Dockerfile em `app/` |
| Monitoramento do laboratório | Total de visitas, gráfico Chart.js por minuto, tabela dos últimos acessos e atualização a cada 10 segundos |
| Terraform | Plano padrão alterado para `free-1-1gb` (verificar disponibilidade); execução de infra manual para evitar provisionamento acidental |
| Verificação neste ambiente em 24/11 | 10 testes do módulo cliente aprovados com dependência psycopg2 simulada; Python compileall, Jinja, JavaScript e YAML sem erros sintáticos |
| Validação local às 19:14 BRT | Primeira execução: 20 aprovados e 1 falha por expectativa incorreta no teste do painel. Após cobrir os estados com e sem dados: 22 aprovados. Flake8 e compilação Python aprovados. O banco e a API são simulados pela suíte. |

## Etapas do laboratório

| # | Etapa | Data/hora | O que fiz | Resultado (checkpoint) | Evidência |
|---|---|---|---|---|---|
| 1 | Conta e projeto na Aiven | _preencher_ | | Tela inicial do projeto, sem serviços | `evidencias/01-...png` |
| 2 | Token de API da Aiven | _preencher_ | | Token gerado (**não** colar o valor aqui) | `evidencias/02-...png` |
| 3 | Repositório no GitHub | _preencher_ | | Arquivos enviados, incluindo `.github/workflows` | `evidencias/03-...png` |
| 4 | Secrets no GitHub | _preencher_ | | 4 secrets cadastrados (só os nomes) | `evidencias/04-...png` |
| 5 | Provisionar o Postgres (Terraform) | _preencher_ | | Workflow verde; serviço `dashboard-pg` **Running** | `evidencias/05-...png` |
| 6 | Serviço no Render | _preencher_ | | Web Service criado com Dockerfile da raiz | `evidencias/06-...png` |
| 7 | Variáveis de ambiente no Render | _preencher_ | | `AIVEN_DB_URL` e `PORT=8080` | `evidencias/07-...png` |
| 8 | Deploy hook → secret no GitHub | _preencher_ | | `RENDER_DEPLOY_HOOK_URL` e `APP_HEALTHCHECK_URL` | `evidencias/08-...png` |
| 9 | Disparar o CI/CD | _preencher_ | | Jobs *test*, *build-and-push* e *deploy* verdes | `evidencias/09-...png` |
| 10 | Validar o painel | _preencher_ | | Painel abre, mostra as cidades, `/healthz` retorna `ok` | `evidencias/10-...png` |

## Problemas encontrados e como resolvi

| Data/hora | Problema (mensagem de erro) | Causa | Solução |
|---|---|---|---|
| _preencher_ | | | |

## Observações finais

_Escreva aqui o que aprendeu e o que mudaria._

## Revisão de conformidade com o guia (24/11/2026)

- Corrigida a posição do Dockerfile para `app/Dockerfile`, compatível com o passo 6 do guia (Root Directory `app`).
- Adicionada persistência e consulta de contagens por minuto e tabela de acessos recentes, cobrindo o checkpoint 10.
- Atualização de métricas a cada 10 segundos em `GET /api/visitas`, sem somar acessos falsos.
- Ajustado Terraform para usar o plano gratuito por padrão e evitar acionamento automático repetido.
- Registro de validação parcial em `evidencias/VALIDACAO_CLIENTE.txt` (testes do cliente com dependência mockada).
- **Não inventar evidências de nuvem:** todos os campos acima exigem imagens e datas reais das suas contas.

## Configuração em 24/11/2026

- Guia oficial aberto e conferido após recebimento da senha.
- GitHub: repositório privado inicialmente vazio, inicializado em `main`. Os arquivos de evidência local incluem a execução inicial e a execução após o ajuste do teste.
- Terraform: workflow manual com opções `validate`, `plan` e `apply`. O workflow fixa PostgreSQL no plano gratuito e desativa Kafka e Grafana.
- Render: Blueprint preparado com plano Free, Docker, raiz `app` e health check `/healthz`. A operação depende da Service URI da Aiven e dos secrets do GitHub.
- Pendências de nuvem: verificar secrets, provisionamento do PostgreSQL, primeiro deploy do Render, execução integral do pipeline, URL pública e métricas de visitas em produção.

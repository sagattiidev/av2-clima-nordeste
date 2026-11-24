# Registro de eventos da AV2

**Aluno** Miqueias Souza dos Santos  
**Projeto** Clima do Nordeste

## 24/11/2026

| Etapa | Resultado | Evidência |
|---|---|---|
| Adaptação do painel | Fonte de dados alterada para Open-Meteo. O painel usa PostgreSQL para os dados climáticos e as métricas de acesso. | [Código da aplicação](app/) |
| Testes locais | Às 19h14, a primeira execução teve 20 aprovações e uma falha. Após corrigir a expectativa do teste e cobrir o cenário sem dados, os 22 testes passaram. Flake8 e compilação Python também passaram. | [Primeira execução](evidencias/VALIDACAO_LOCAL_INICIAL.txt) · [Execução final](evidencias/VALIDACAO_LOCAL.txt) |
| Publicação no GitHub | Código e workflows enviados à branch `main`. | [Verificação no GitHub](evidencias/VERIFICACAO_GITHUB.md) |
| Configuração da Aiven e do Render | Workflow Terraform preparado para PostgreSQL Free. Blueprint do Render preparado para Docker, plano Free e verificação em `/healthz`. | [Workflow Terraform](.github/workflows/infra.yml) · [Blueprint](render.yaml) |

## Secrets da Aiven

Às 19h28 (Brasília), a captura das configurações do repositório mostrou `AIVEN_API_TOKEN` e `AIVEN_PROJECT` cadastrados. A validade das credenciais será verificada na execução do Terraform.

## Execuções no GitHub Actions

- O [CI/CD](https://github.com/sagattiidev/av2-clima-nordeste/actions/runs/45499331723) aprovou testes e lint e publicou a imagem no GHCR. O hook e o health check do Render foram pulados.
- A [execução de infraestrutura das 19h30](https://github.com/sagattiidev/av2-clima-nordeste/actions/runs/45501546825) iniciou o Terraform, mas falhou na validação porque o provider Aiven 4.66.0 não expõe `ca_cert` no recurso Kafka. O `plan` e o `apply` foram pulados. A saída incompatível foi removida.

## Pendências

- Execução do Terraform e configuração dos secrets do Render.
- Provisionamento do PostgreSQL, deploy e verificação da URL pública e das métricas de acesso.


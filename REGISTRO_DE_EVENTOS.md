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

- Às 19h32, o [novo plan](https://github.com/sagattiidev/av2-clima-nordeste/actions/runs/45501796199) passou. O Terraform planejou três adições (serviço PostgreSQL no plano `free-1-1gb`, banco e usuário), zero alterações e zero exclusões. O `apply` foi pulado.

- Às 19h34, o [apply](https://github.com/sagattiidev/av2-clima-nordeste/actions/runs/45502214039) passou na validação e no planejamento, mas falhou na criação do PostgreSQL. A Aiven retornou `404 ServiceCreate`: o plano `free-1-1gb` está indisponível em `google-southamerica-east1`. O serviço não foi criado nessa execução.

- Às 19h37, o serviço `dashboard-pg` apareceu no console da Aiven no projeto `av2-miqueias`, após criação manual no plano Free da América do Norte. O status estava `Building` (9%). A conexão com o banco segue pendente de validação.

- Às 19h41, o console da Aiven mostrou `dashboard-pg` com status `Running` e a mensagem `Your service is ready`. Falta testar a conexão a partir do Render.

- Às 19h54, o [painel no Render](https://av2-clima-nordeste.onrender.com) e `/healthz` responderam HTTP 200. O health check retornou `{"status":"ok"}`; `/api/visitas` retornou o total, os acessos recentes e a contagem por minuto. A consulta de clima para Recife respondeu HTTP 200 com histórico vazio. O teste de atualização manual retornou HTTP 502 porque a Open-Meteo respondeu HTTP 429 (Too Many Requests) à consulta feita pelo Render.

- O [CI/CD completo](https://github.com/sagattiidev/av2-clima-nordeste/actions/runs/45506067037) aprovou testes, lint e publicação da imagem no GHCR. O job do Render executou o deploy hook e passou no health check (`{"status":"ok"}`). Uma nova consulta à API de clima para Recife ainda retornou histórico vazio.

## Pendências

- Validar a carga de dados climáticos após a Open-Meteo voltar a aceitar as requisições do Render.


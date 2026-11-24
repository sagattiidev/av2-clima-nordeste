# Checklist de conformidade — AV2

**Aluno:** Miqueias Souza dos Santos  
**Prazo do enunciado:** 24/11, até 23:59, no Canvas  
**Entrega:** AV2_MIQUEIAS_SOUZA_DOS_SANTOS.zip

## O que está no arquivo

- [x] Projeto de referência modificado para outra fonte de dados abertos: Open-Meteo, 5 capitais nordestinas.
- [x] Interface própria com indicadores e gráfico meteorológico.
- [x] Registro de visitas em PostgreSQL (tabela `visits`).
- [x] Gráfico Chart.js de acessos por minuto, tabela dos últimos acessos e atualização 10 s.
- [x] Dockerfile dentro de `app/` para configurar **Root Directory = app** no Render.
- [x] GitHub Actions: Terraform manual, testes/build/deploy com check `/healthz`.
- [x] Registro de eventos e relatório técnico.

## Etapas do guia

- [ ] **1 — Aiven:** conta/projeto criado (`evidencias/01-aiven-projeto.png`).
- [ ] **2 — Token Aiven:** gerado; print somente com nome, nunca com o token (`02-token-criado.png`).
- [x] **3 — GitHub:** repositório com `app`, `terraform` e `.github/workflows`. [Evidência](evidencias/VERIFICACAO_GITHUB.md)
- [ ] **4 — Secrets:** 4 nomes configurados no Actions, valores ocultos (`04-secrets.png`).
- [ ] **5 — Terraform:** workflow concluído + PostgreSQL Running (`05-infra-postgres.png`).
- [ ] **6 — Render:** Web Service com Root Directory `app` / Docker (`06-servico-render.png`).
- [ ] **7 — Variável Render:** `AIVEN_DB_URL` cadastrada, sem mostrar valor (`07-variavel-render.png`).
- [ ] **8 — Deploy hook:** secret `RENDER_DEPLOY_HOOK_URL` cadastrado (`08-deploy-hook.png`).
- [ ] **9 — CI/CD:** jobs test, build-and-push, deploy verdes (`09-pipeline.png`).
- [ ] **10 — Dashboard:** URL pública, contador de visitas, gráfico de acessos e tabela atualizados (`10-dashboard.png`).

**Custo:** o Terraform usa plano gratuito `free-1-1gb` por padrão; confirme a disponibilidade em sua conta. Não altere para `hobbyist` sem verificar o custo. Não rode `terraform apply` repetidamente sem state persistente.

**Referência:** checklist conferido com as dez etapas do PDF oficial da atividade.

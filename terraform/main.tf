terraform {
  required_providers {
    aiven = {
      source  = "aiven/aiven"
      version = "~> 4.0"
    }
  }

  # Backend remoto opcional (recomendado em turma: cada aluno usa seu bucket/workspace,
  # ou usa-se o backend local do runner do GitHub Actions, que é efêmero mas suficiente
  # para o laboratório).
  # backend "s3" { ... }
}

provider "aiven" {
  api_token = var.aiven_api_token
}

resource "aiven_pg" "dashboard_db" {
  project                 = var.aiven_project
  # Free nao permite escolher nuvem/regiao; null omite o campo.
  cloud_name              = startswith(var.pg_plan, "free-") ? null : var.cloud_name
  plan                    = var.pg_plan
  service_name            = var.service_name
  maintenance_window_dow  = "sunday"
  maintenance_window_time = "03:00:00"
}

resource "aiven_pg_database" "dashboard" {
  project       = var.aiven_project
  service_name  = aiven_pg.dashboard_db.service_name
  database_name = var.database_name
}

resource "aiven_pg_user" "app_user" {
  project      = var.aiven_project
  service_name = aiven_pg.dashboard_db.service_name
  username     = var.db_username
}

# ---------------------------------------------------------------------------
# Kafka — ingestão de eventos (produtor publica, consumidor grava no Postgres)
# ---------------------------------------------------------------------------
# OPCIONAL (enable_kafka = false por padrão). Ao contrário do Postgres (plano
# "free-1-1gb" (plano gratuito, sujeito à disponibilidade)), o Aiven for Apache Kafka
# normalmente exige um plano pago (ex: "startup-2"). Ligue só se a sua conta
# permitir; senão o `terraform apply` falha por causa dele.
resource "aiven_kafka" "events" {
  count        = var.enable_kafka ? 1 : 0
  project      = var.aiven_project
  cloud_name   = var.cloud_name
  plan         = var.kafka_plan
  service_name = var.kafka_service_name

  kafka_user_config {
    kafka_authentication_methods {
      # SASL facilita autenticação via usuário/senha em vez de certificado
      # mTLS — mais simples de guardar como Secret no GitHub/Render.
      sasl = true
    }
  }
}

resource "aiven_kafka_topic" "clima_nordeste" {
  count        = var.enable_kafka ? 1 : 0
  project      = var.aiven_project
  service_name = aiven_kafka.events[0].service_name
  topic_name   = var.kafka_topic_name
  partitions   = 1
  replication  = 2
}

# ---------------------------------------------------------------------------
# Grafana — exploração visual dos dados do Postgres
# ---------------------------------------------------------------------------
# OPCIONAL (enable_grafana = false por padrão).
resource "aiven_grafana" "dashboards" {
  count        = var.enable_grafana ? 1 : 0
  project      = var.aiven_project
  cloud_name   = var.cloud_name
  plan         = var.grafana_plan
  service_name = var.grafana_service_name
}

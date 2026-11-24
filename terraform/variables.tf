variable "aiven_api_token" {
  description = "Token de API da Aiven (Aiven Console > Profile > Authentication tokens)"
  type        = string
  sensitive   = true
}

variable "aiven_project" {
  description = "Nome do projeto na Aiven"
  type        = string
}

variable "cloud_name" {
  description = "Região/nuvem da Aiven, ex: google-southamerica-east1, aws-sa-east-1"
  type        = string
  default     = "google-southamerica-east1"
}

variable "pg_plan" {
  description = "Plano PostgreSQL. Default gratuito: free-1-1gb. Nao escolha hobbyist sem verificar custos."
  type        = string
  default     = "free-1-1gb"
}

variable "service_name" {
  description = "Nome do serviço PostgreSQL"
  type        = string
  default     = "dashboard-pg"
}

variable "database_name" {
  description = "Nome do banco de dados"
  type        = string
  default     = "dashboard"
}

variable "db_username" {
  description = "Usuário de aplicação para o Postgres"
  type        = string
  default     = "dashboard_app"
}

variable "kafka_plan" {
  description = "Plano do serviço Kafka (normalmente pago — verifique disponibilidade na conta)"
  type        = string
  default     = "startup-2"
}

variable "kafka_service_name" {
  description = "Nome do serviço Kafka"
  type        = string
  default     = "clima-kafka"
}

variable "kafka_topic_name" {
  description = "Nome do tópico usado para os eventos de clima"
  type        = string
  default     = "clima-nordeste"
}

variable "grafana_plan" {
  description = "Plano do serviço Grafana"
  type        = string
  default     = "startup-1"
}

variable "grafana_service_name" {
  description = "Nome do serviço Grafana"
  type        = string
  default     = "clima-grafana"
}

variable "enable_kafka" {
  description = "Provisiona o Aiven for Apache Kafka (normalmente pago). Deixe false no laboratório básico."
  type        = bool
  default     = false
}

variable "enable_grafana" {
  description = "Provisiona o Aiven for Grafana. Deixe false no laboratório básico."
  type        = bool
  default     = false
}

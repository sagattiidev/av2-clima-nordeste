output "pg_service_uri" {
  description = "String de conexão completa do serviço PostgreSQL (marcada como sensível)"
  value       = aiven_pg.dashboard_db.service_uri
  sensitive   = true
}

output "pg_host" {
  value = aiven_pg.dashboard_db.service_host
}

output "pg_port" {
  value = aiven_pg.dashboard_db.service_port
}

output "kafka_bootstrap_servers" {
  description = "host:port para KAFKA_BOOTSTRAP_SERVERS (null se enable_kafka = false)"
  value       = try("${aiven_kafka.events[0].service_host}:${aiven_kafka.events[0].service_port}", null)
}

output "kafka_username" {
  value     = try(aiven_kafka.events[0].service_username, null)
  sensitive = true
}

output "kafka_password" {
  value     = try(aiven_kafka.events[0].service_password, null)
  sensitive = true
}

output "kafka_ca_cert" {
  description = "Certificado CA — cole em KAFKA_CA_CERT_PEM no GitHub/Render"
  value       = try(aiven_kafka.events[0].ca_cert, null)
  sensitive   = true
}

output "grafana_uri" {
  description = "URL pública do Grafana provisionado (null se enable_grafana = false)"
  value       = try(aiven_grafana.dashboards[0].service_uri, null)
  sensitive   = true
}

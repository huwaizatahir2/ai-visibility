output "app_public_ip" {
  description = "Elastic IP of the app host (point DNS here)."
  value       = aws_eip.app.public_ip
}

output "db_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port)."
  value       = aws_db_instance.main.endpoint
}

output "db_password_ssm_parameter" {
  description = "SSM parameter holding the DB master password."
  value       = aws_ssm_parameter.db_password.name
}

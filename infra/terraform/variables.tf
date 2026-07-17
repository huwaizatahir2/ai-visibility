variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Name prefix for resources (usually the org/workspace name)."
  type        = string
  default     = "ai-visibility"
}

variable "instance_type" {
  description = "EC2 instance type for the app host."
  type        = string
  default     = "t3.small"
}

variable "db_instance_class" {
  description = "RDS instance class for PostgreSQL."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "ai_visibility"
}

variable "db_username" {
  description = "PostgreSQL master username."
  type        = string
  default     = "ai_visibility"
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair for SSH access."
  type        = string
}

variable "admin_cidr" {
  description = "CIDR allowed to SSH to the app host (your office/VPN)."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "backup_retention_days" {
  description = "RDS automated backup retention (days)."
  type        = number
  default     = 7
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "minimal"

  validation {
    condition     = contains(["minimal", "dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: minimal, dev, staging, prod"
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "mantrix"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

# RDS Configuration
variable "rds_instance_class" {
  description = "Instance class for RDS PostgreSQL"
  type        = string
  default     = "db.t3.micro"  # Minimal for testing
}

variable "rds_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 20  # Minimum for PostgreSQL
}

variable "rds_database_name" {
  description = "Name of the database to create"
  type        = string
  default     = "mantrix_madison"
}

variable "rds_username" {
  description = "Master username for RDS"
  type        = string
  default     = "mantrix"
  sensitive   = true
}

# ElastiCache Configuration
variable "redis_node_type" {
  description = "Node type for ElastiCache Redis"
  type        = string
  default     = "cache.t3.micro"  # Minimal for testing
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1  # Single node for minimal deployment
}

# ECS Configuration
variable "backend_cpu" {
  description = "CPU units for backend task (1024 = 1 vCPU)"
  type        = number
  default     = 512  # 0.5 vCPU for minimal
}

variable "backend_memory" {
  description = "Memory for backend task in MB"
  type        = number
  default     = 1024  # 1 GB for minimal
}

variable "frontend_cpu" {
  description = "CPU units for frontend task"
  type        = number
  default     = 256  # 0.25 vCPU for minimal
}

variable "frontend_memory" {
  description = "Memory for frontend task in MB"
  type        = number
  default     = 512  # 512 MB for minimal
}

variable "backend_desired_count" {
  description = "Desired number of backend tasks"
  type        = number
  default     = 1  # Single instance for minimal
}

variable "frontend_desired_count" {
  description = "Desired number of frontend tasks"
  type        = number
  default     = 1  # Single instance for minimal
}

# Secrets Manager ARNs (to be created separately)
variable "anthropic_api_key_arn" {
  description = "ARN of Anthropic API key in Secrets Manager"
  type        = string
  default     = ""
}

variable "openai_api_key_arn" {
  description = "ARN of OpenAI API key in Secrets Manager"
  type        = string
  default     = ""
}

variable "cognito_pool_id_arn" {
  description = "ARN of Cognito Pool ID in Secrets Manager"
  type        = string
  default     = ""
}

variable "cognito_client_id_arn" {
  description = "ARN of Cognito Client ID in Secrets Manager"
  type        = string
  default     = ""
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
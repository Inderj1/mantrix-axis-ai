variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "mantrix-madison"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "madisonreed.cloudmantra.ai"
}

variable "instance_type" {
  description = "EC2 instance type (t3.medium = 2 vCPU, 4GB RAM)"
  type        = string
  default     = "t3.medium"
}

variable "root_volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 30
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "allowed_ssh_cidrs" {
  description = "List of CIDR blocks allowed to SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "key_name" {
  description = "Name of the SSH key pair"
  type        = string
  default     = "mantrix-madison-key"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key file"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_user" {
  description = "SSH username"
  type        = string
  default     = "ubuntu"
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID for cloudmantra.ai (optional)"
  type        = string
  default     = ""
}

variable "use_route53" {
  description = "Whether to create Route53 DNS record"
  type        = bool
  default     = false
}

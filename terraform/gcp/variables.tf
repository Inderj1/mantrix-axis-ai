variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-a"
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

variable "machine_type" {
  description = "GCP machine type (e2-medium = 2 vCPU, 4GB RAM ~= t3.medium)"
  type        = string
  default     = "e2-medium"
}

variable "disk_size_gb" {
  description = "Boot disk size in GB"
  type        = number
  default     = 30
}

variable "ssh_user" {
  description = "SSH username"
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "use_cloud_dns" {
  description = "Use Cloud DNS for domain management"
  type        = bool
  default     = false
}

variable "dns_zone_name" {
  description = "Cloud DNS managed zone name (if use_cloud_dns is true)"
  type        = string
  default     = ""
}

output "instance_id" {
  description = "GCP instance ID"
  value       = google_compute_instance.mantrix_vm.id
}

output "instance_name" {
  description = "Name of the compute instance"
  value       = google_compute_instance.mantrix_vm.name
}

output "instance_public_ip" {
  description = "Public IP address of the instance"
  value       = google_compute_address.mantrix_ip.address
}

output "instance_zone" {
  description = "Zone where the instance is deployed"
  value       = google_compute_instance.mantrix_vm.zone
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh ${var.ssh_user}@${google_compute_address.mantrix_ip.address}"
}

output "application_url_http" {
  description = "Application URL (HTTP)"
  value       = "http://${google_compute_address.mantrix_ip.address}"
}

output "application_domain" {
  description = "Application domain URL (HTTPS)"
  value       = "https://${var.domain_name}"
}

output "frontend_url" {
  description = "Frontend URL (port 3000)"
  value       = "http://${google_compute_address.mantrix_ip.address}:3000"
}

output "backend_api_url" {
  description = "Backend API URL (port 5001)"
  value       = "http://${google_compute_address.mantrix_ip.address}:5001"
}

output "vpc_id" {
  description = "VPC network ID"
  value       = google_compute_network.mantrix_vpc.id
}

output "vpc_name" {
  description = "VPC network name"
  value       = google_compute_network.mantrix_vpc.name
}

output "subnet_id" {
  description = "Subnet ID"
  value       = google_compute_subnetwork.mantrix_subnet.id
}

output "dns_configuration" {
  description = "DNS A record to configure manually"
  value       = "${var.domain_name} -> ${google_compute_address.mantrix_ip.address}"
}

output "deployment_instructions" {
  description = "Next steps for deployment"
  value       = <<-EOT
    ========================================
    Mantrix Madison Reed - Deployment Instructions
    ========================================

    1. Configure DNS:
       Point ${var.domain_name} to ${google_compute_address.mantrix_ip.address}

    2. SSH to instance:
       ssh ${var.ssh_user}@${google_compute_address.mantrix_ip.address}

    3. Clone repository:
       cd /opt/mantrix
       git clone https://github.com/cloudmantra-ai/mantrix.unified-madison.git .
       git checkout demo/madison

    4. Configure environment:
       cp .env.example .env
       # Edit .env with your API keys and secrets

    5. Start application:
       docker-compose up -d

    6. Configure SSL:
       sudo certbot --nginx -d ${var.domain_name}

    7. Access application:
       https://${var.domain_name}

    ========================================
    Logs: ssh ${var.ssh_user}@${google_compute_address.mantrix_ip.address} "sudo tail -f /var/log/startup-script.log"
    ========================================
  EOT
}

output "gcp_console_url" {
  description = "GCP Console URL for the instance"
  value       = "https://console.cloud.google.com/compute/instancesDetail/zones/${var.zone}/instances/${google_compute_instance.mantrix_vm.name}?project=${var.project_id}"
}

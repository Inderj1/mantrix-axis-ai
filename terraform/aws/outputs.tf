output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.mantrix_ec2.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.mantrix_eip.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.mantrix_ec2.public_dns
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/id_rsa ${var.ssh_user}@${aws_eip.mantrix_eip.public_ip}"
}

output "application_url" {
  description = "Application URL (HTTP)"
  value       = "http://${aws_eip.mantrix_eip.public_ip}"
}

output "application_domain" {
  description = "Application domain URL"
  value       = "https://${var.domain_name}"
}

output "frontend_url" {
  description = "Frontend URL (port 3000)"
  value       = "http://${aws_eip.mantrix_eip.public_ip}:3000"
}

output "backend_api_url" {
  description = "Backend API URL (port 5001)"
  value       = "http://${aws_eip.mantrix_eip.public_ip}:5001"
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.mantrix_vpc.id
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.mantrix_sg.id
}

output "dns_configuration" {
  description = "DNS A record to configure manually"
  value       = "${var.domain_name} -> ${aws_eip.mantrix_eip.public_ip}"
}

output "deployment_instructions" {
  description = "Next steps for deployment"
  value       = <<-EOT
    1. Configure DNS: Point ${var.domain_name} to ${aws_eip.mantrix_eip.public_ip}
    2. SSH to instance: ssh -i ~/.ssh/id_rsa ${var.ssh_user}@${aws_eip.mantrix_eip.public_ip}
    3. Wait for startup script to complete (check /var/log/cloud-init-output.log)
    4. Access application: http://${aws_eip.mantrix_eip.public_ip}:3000
  EOT
}

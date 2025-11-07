# Mantrix Madison Reed - GCP Terraform Deployment

Deploy Mantrix Madison Reed application on Google Cloud Platform.

## Prerequisites

1. **GCP Project** with billing enabled
2. **gcloud CLI** configured (`gcloud auth login`)
3. **Terraform** >= 1.0
4. **SSH key pair** (~/.ssh/id_rsa.pub)

## Infrastructure

- **Machine**: e2-medium (2 vCPU, 4GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 30GB SSD
- **Domain**: madisonreed.cloudmantra.ai
- **Cost**: ~$27/month

## Quick Start

```bash
# 1. Set GCP project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# 2. Enable APIs
gcloud services enable compute.googleapis.com

# 3. Configure
cd terraform/gcp
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id

# 4. Deploy
terraform init
terraform plan
terraform apply

# 5. Get IP address
terraform output instance_public_ip
```

## Post-Deployment

### 1. Configure DNS
Point `madisonreed.cloudmantra.ai` to the static IP from `terraform output`

### 2. SSH to instance
```bash
ssh ubuntu@<STATIC_IP>
```

### 3. Clone repository
```bash
cd /opt/mantrix
sudo git clone https://github.com/cloudmantra-ai/mantrix.unified-madison.git .
sudo chown -R ubuntu:ubuntu /opt/mantrix
git checkout demo/madison
```

### 4. Configure environment
```bash
# Copy and edit environment files
cp /opt/mantrix/.env.example /opt/mantrix/.env
# Add your API keys to .env
```

### 5. Start application
```bash
cd /opt/mantrix
docker-compose up -d
```

### 6. Setup SSL
```bash
sudo certbot --nginx -d madisonreed.cloudmantra.ai
```

### 7. Verify
Visit: https://madisonreed.cloudmantra.ai

## Management

```bash
# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Deploy updates
cd /opt/mantrix && git pull && docker-compose up -d --build

# Check status
docker-compose ps
```

## Outputs

```bash
terraform output                    # All outputs
terraform output instance_public_ip # Just IP
terraform output ssh_command        # SSH command
terraform output deployment_instructions # Full guide
```

## Cleanup

```bash
terraform destroy
```

## Cost Optimization

- Development: Use `e2-small` (~$13/month)
- Stop when not needed: `gcloud compute instances stop mantrix-madison-vm --zone=us-central1-a`
- Restart: `gcloud compute instances start mantrix-madison-vm --zone=us-central1-a`

## Troubleshooting

```bash
# Check startup logs
ssh ubuntu@<IP> "sudo tail -f /var/log/startup-script.log"

# Check services
ssh ubuntu@<IP> "docker-compose ps"

# Check nginx
ssh ubuntu@<IP> "sudo systemctl status nginx"

# Serial console
gcloud compute instances get-serial-port-output mantrix-madison-vm --zone=us-central1-a
```

## Support

- GCP Console: `terraform output gcp_console_url`
- Logs: `/var/log/startup-script.log`
- Nginx: `/var/log/nginx/error.log`

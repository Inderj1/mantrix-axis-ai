# Mantrix Madison Reed - AWS Terraform Deployment

This directory contains Terraform configuration to deploy Mantrix Madison Reed application on AWS EC2.

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform installed** (>= 1.0)
3. **SSH key pair** generated (~/.ssh/id_rsa and ~/.ssh/id_rsa.pub)

## Infrastructure

- **Instance Type**: t3.medium (2 vCPU, 4GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 30GB GP3 SSD
- **Domain**: madisonreed.cloudmantra.ai

## Quick Start

### 1. Copy and configure variables

```bash
cd terraform/aws
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your settings:
- Update `aws_region` if needed
- Update `ssh_public_key_path` to your SSH public key path
- Optionally configure Route53 settings

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Review the plan

```bash
terraform plan
```

### 4. Deploy

```bash
terraform apply
```

Type `yes` when prompted.

### 5. Get outputs

```bash
terraform output
```

## Post-Deployment Steps

### 1. Configure DNS

Point `madisonreed.cloudmantra.ai` to the Elastic IP from terraform output:

```bash
terraform output instance_public_ip
```

Either:
- Set `use_route53 = true` in terraform.tfvars and provide `route53_zone_id`
- Or manually configure DNS A record in your DNS provider

### 2. SSH to instance

```bash
ssh -i ~/.ssh/id_rsa ubuntu@<ELASTIC_IP>
```

### 3. Clone repository

```bash
cd /opt/mantrix
sudo chown ubuntu:ubuntu /opt/mantrix
git clone https://github.com/cloudmantra-ai/mantrix.unified-madison.git .
git checkout demo/madison
```

### 4. Configure environment variables

Create `.env` files for backend and frontend:

**Backend** (`/opt/mantrix/backend/.env`):
```env
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=your-secret-key-here
MONGODB_URI=mongodb://localhost:27017/mantrix
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

**Frontend** (`/opt/mantrix/frontend/.env`):
```env
REACT_APP_API_URL=https://madisonreed.cloudmantra.ai/api
REACT_APP_CLERK_PUBLISHABLE_KEY=your-clerk-key
```

### 5. Start application with Docker Compose

```bash
cd /opt/mantrix
docker-compose up -d
```

### 6. Configure SSL Certificate

```bash
sudo certbot --nginx -d madisonreed.cloudmantra.ai
```

Follow prompts to configure SSL.

### 7. Verify deployment

- Frontend: https://madisonreed.cloudmantra.ai
- Backend API: https://madisonreed.cloudmantra.ai/api/health

## Management Commands

### View logs
```bash
docker-compose logs -f
```

### Restart services
```bash
docker-compose restart
```

### Stop services
```bash
docker-compose down
```

### Update deployment
```bash
cd /opt/mantrix
git pull origin demo/madison
docker-compose down
docker-compose up -d --build
```

## Monitoring

Check startup script logs:
```bash
sudo tail -f /var/log/cloud-init-output.log
```

Check nginx logs:
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Security

- SSH access is restricted by security group (configure `allowed_ssh_cidrs` in terraform.tfvars)
- Root volume is encrypted
- UFW firewall is enabled
- IMDSv2 is required for EC2 metadata

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

## Troubleshooting

### Check if services are running
```bash
docker-compose ps
```

### Check nginx status
```bash
sudo systemctl status nginx
```

### Test nginx configuration
```bash
sudo nginx -t
```

### Restart nginx
```bash
sudo systemctl restart nginx
```

## Cost Estimation

- **EC2 t3.medium**: ~$30/month (on-demand pricing)
- **EBS GP3 30GB**: ~$2.40/month
- **Data Transfer**: Variable based on usage
- **Elastic IP**: Free while attached to running instance

**Total**: ~$32-35/month (excluding data transfer)

#!/bin/bash
set -e

# Logging
exec > >(tee /var/log/startup-script.log)
exec 2>&1

echo "========================================="
echo "Mantrix Madison Reed - EC2 Startup Script"
echo "Started at: $(date)"
echo "========================================="

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install Docker Compose standalone
echo "Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="2.23.3"
curl -SL https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Install Node.js (v18 LTS)
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

# Install Git
echo "Installing Git..."
apt-get install -y git

# Install nginx
echo "Installing nginx..."
apt-get install -y nginx

# Install certbot for SSL
echo "Installing certbot..."
apt-get install -y certbot python3-certbot-nginx

# Create application directory
echo "Creating application directory..."
mkdir -p /opt/mantrix
chown -R ubuntu:ubuntu /opt/mantrix

# Install PM2 globally
echo "Installing PM2..."
npm install -g pm2

# Configure firewall
echo "Configuring UFW firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw allow 3000/tcp  # Frontend
ufw allow 5001/tcp  # Backend API

# Create systemd service for application (optional)
cat > /etc/systemd/system/mantrix.service <<'EOF'
[Unit]
Description=Mantrix Madison Reed Application
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/mantrix
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
EOF

# Set up nginx reverse proxy configuration
cat > /etc/nginx/sites-available/mantrix <<'EOF'
server {
    listen 80;
    server_name madisonreed.cloudmantra.ai;

    client_max_body_size 100M;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable nginx site
ln -sf /etc/nginx/sites-available/mantrix /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

# Restart nginx
systemctl restart nginx
systemctl enable nginx

# Create deployment script
cat > /opt/mantrix/deploy.sh <<'DEPLOY_EOF'
#!/bin/bash
set -e

echo "Deploying Mantrix Madison Reed..."

# Pull latest code
cd /opt/mantrix
git pull origin demo/madison

# Build and restart containers
docker-compose down
docker-compose up -d --build

echo "Deployment complete!"
DEPLOY_EOF

chmod +x /opt/mantrix/deploy.sh

# Set ownership
chown -R ubuntu:ubuntu /opt/mantrix

# Create helpful aliases
cat >> /home/ubuntu/.bashrc <<'ALIAS_EOF'

# Mantrix aliases
alias mantrix-logs='docker-compose -f /opt/mantrix/docker-compose.yml logs -f'
alias mantrix-status='docker-compose -f /opt/mantrix/docker-compose.yml ps'
alias mantrix-restart='docker-compose -f /opt/mantrix/docker-compose.yml restart'
alias mantrix-deploy='cd /opt/mantrix && ./deploy.sh'
ALIAS_EOF

echo "========================================="
echo "Startup script completed at: $(date)"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Clone the repository to /opt/mantrix"
echo "2. Configure environment variables"
echo "3. Run docker-compose up -d"
echo "4. Configure SSL with: sudo certbot --nginx -d madisonreed.cloudmantra.ai"
echo "========================================="

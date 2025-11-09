#!/bin/bash
set -e

# Logging
exec > >(tee /var/log/startup-script.log)
exec 2>&1

echo "========================================="
echo "Mantrix DrinkAZ - GCP Startup Script"
echo "Started at: $(date)"
echo "========================================="

# Wait for network
sleep 10

# Update system
echo "Updating system packages..."
apt-get update
export DEBIAN_FRONTEND=noninteractive
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

# Install additional utilities
apt-get install -y htop vim wget unzip

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

# Create systemd service for application
cat > /etc/systemd/system/mantrix.service <<'EOF'
[Unit]
Description=Mantrix DrinkAZ Application
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
    server_name drinkaz-axis.cloudmantra.ai;

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

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
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

        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
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

echo "Deploying Mantrix DrinkAZ..."

# Pull latest code
cd /opt/mantrix
git pull origin nov06-agent-mode

# Build and restart containers
docker-compose down
docker-compose up -d --build

echo "Deployment complete!"
echo "Frontend: http://$(hostname -I | awk '{print $1}'):3000"
echo "Backend: http://$(hostname -I | awk '{print $1}'):5001"
DEPLOY_EOF

chmod +x /opt/mantrix/deploy.sh

# Create helpful aliases
cat >> /home/ubuntu/.bashrc <<'ALIAS_EOF'

# Mantrix aliases
alias mantrix-logs='docker-compose -f /opt/mantrix/docker-compose.yml logs -f'
alias mantrix-status='docker-compose -f /opt/mantrix/docker-compose.yml ps'
alias mantrix-restart='docker-compose -f /opt/mantrix/docker-compose.yml restart'
alias mantrix-deploy='cd /opt/mantrix && ./deploy.sh'
alias mantrix-logs-backend='docker-compose -f /opt/mantrix/docker-compose.yml logs -f backend'
alias mantrix-logs-frontend='docker-compose -f /opt/mantrix/docker-compose.yml logs -f frontend'
ALIAS_EOF

# Set ownership
chown -R ubuntu:ubuntu /opt/mantrix

# Create environment file template
cat > /opt/mantrix/.env.example <<'ENV_EOF'
# Database Configuration
MONGODB_URI=mongodb://localhost:27017/mantrix
REDIS_URL=redis://localhost:6379/0

# Application
NODE_ENV=production
FLASK_ENV=production
FLASK_APP=app.py

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here

# AI Services
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Clerk Authentication
REACT_APP_CLERK_PUBLISHABLE_KEY=your-clerk-key
CLERK_SECRET_KEY=your-clerk-secret

# Domain
DOMAIN=drinkaz-axis.cloudmantra.ai
REACT_APP_API_URL=https://drinkaz-axis.cloudmantra.ai/api
ENV_EOF

echo "========================================="
echo "Startup script completed at: $(date)"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Clone the repository to /opt/mantrix"
echo "   git clone -b nov06-agent-mode https://github.com/Inderj1/mantrix-axis-ai.git /opt/mantrix"
echo "2. Create .env file from .env.example"
echo "3. Run docker-compose up -d"
echo "4. Configure SSL: sudo certbot --nginx -d drinkaz-axis.cloudmantra.ai"
echo ""
echo "Logs: sudo tail -f /var/log/startup-script.log"
echo "========================================="

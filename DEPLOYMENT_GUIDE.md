# Clinic Backend Deployment Guide

Complete deployment approaches for **Online** (Cloud) and **Offline** (On-Premises) deployment.

---

## Table of Contents

1. [Online Deployment (Cloud)](#online-deployment-cloud)
   - [Option 1: Railway](#option-1-railway-recommended)
   - [Option 2: Render](#option-2-render)
   - [Option 3: Heroku](#option-3-heroku)
   - [Option 4: AWS EC2](#option-4-aws-ec2)
   - [Option 5: DigitalOcean App Platform](#option-5-digitalocean-app-platform)
   - [Option 6: Google Cloud Run](#option-6-google-cloud-run)

2. [Offline Deployment (On-Premises)](#offline-deployment-on-premises)
   - [Option 1: Docker Deployment](#option-1-docker-deployment-recommended)
   - [Option 2: Traditional Server Setup](#option-2-traditional-server-setup)
   - [Option 3: Single Machine Setup](#option-3-single-machine-setup)

3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Post-Deployment Steps](#post-deployment-steps)
5. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Online Deployment (Cloud)

### Option 1: Railway (Recommended)

**Best for**: Quick deployment, automatic HTTPS, PostgreSQL included

#### Prerequisites
- GitHub account
- Railway account (free tier available)

#### Steps

1. **Prepare Repository**
   ```bash
   # Create Procfile for Railway
   echo "web: gunicorn -w 4 -b 0.0.0.0:\$PORT run:app" > Procfile
   ```

2. **Create railway.json** (optional)
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "gunicorn -w 4 -b 0.0.0.0:$PORT run:app",
       "restartPolicyType": "ON_FAILURE",
       "restartPolicyMaxRetries": 10
     }
   }
   ```

3. **Deploy via Railway Dashboard**
   - Go to https://railway.app
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway auto-detects Flask and installs dependencies

4. **Add PostgreSQL Database**
   - In Railway dashboard, click "New" → "Database" → "PostgreSQL"
   - Railway provides `DATABASE_URL` automatically

5. **Set Environment Variables**
   ```
   SECRET_KEY=<generate-random-key>
   DATABASE_URL=<auto-provided-by-railway>
   FLASK_ENV=production
   ```

6. **Run Migrations**
   ```bash
   # Via Railway CLI or dashboard shell
   railway run flask db upgrade
   ```

7. **Initialize Admin User**
   ```bash
   railway run python init_admin.py
   ```

**Cost**: Free tier available, then ~$5-20/month

---

### Option 2: Render

**Best for**: Free PostgreSQL, easy setup

#### Steps

1. **Create render.yaml**
   ```yaml
   services:
     - type: web
       name: clinic-backend
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: gunicorn -w 4 -b 0.0.0.0:$PORT run:app
       envVars:
         - key: SECRET_KEY
           generateValue: true
         - key: FLASK_ENV
           value: production
         - key: DATABASE_URL
           fromDatabase:
             name: clinic-db
             property: connectionString
   
   databases:
     - name: clinic-db
       plan: free
   ```

2. **Deploy**
   - Connect GitHub repo to Render
   - Render auto-detects `render.yaml`
   - Creates database and web service

3. **Run Migrations**
   - Use Render shell: `flask db upgrade`
   - Or add to build command: `pip install -r requirements.txt && flask db upgrade`

**Cost**: Free tier (sleeps after inactivity), then $7/month

---

### Option 3: Heroku

**Best for**: Mature platform, extensive documentation

#### Steps

1. **Create Procfile**
   ```
   web: gunicorn -w 4 -b 0.0.0.0:$PORT run:app
   worker: celery -A app.celery worker --loglevel=info
   ```

2. **Create runtime.txt**
   ```
   python-3.13.0
   ```

3. **Create app.json** (optional)
   ```json
   {
     "name": "Clinic Backend",
     "description": "Clinic DICOM Management System",
     "repository": "https://github.com/yourusername/clinic-backend",
     "env": {
       "SECRET_KEY": {
         "generator": "secret"
       },
       "FLASK_ENV": {
         "value": "production"
       }
     },
     "addons": [
       "heroku-postgresql:mini",
       "heroku-redis:mini"
     ]
   }
   ```

4. **Deploy**
   ```bash
   # Install Heroku CLI
   heroku login
   heroku create clinic-backend
   heroku addons:create heroku-postgresql:mini
   heroku addons:create heroku-redis:mini
   git push heroku main
   heroku run flask db upgrade
   heroku run python init_admin.py
   ```

**Cost**: $7-25/month (no free tier anymore)

---

### Option 4: AWS EC2

**Best for**: Full control, enterprise needs

#### Steps

1. **Launch EC2 Instance**
   - Ubuntu 22.04 LTS
   - t3.medium or larger
   - Security group: Allow HTTP (80), HTTPS (443), SSH (22)

2. **Setup Server**
   ```bash
   # SSH into instance
   ssh -i your-key.pem ubuntu@your-ec2-ip
   
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install Python, PostgreSQL, Redis, Nginx
   sudo apt install -y python3.13 python3-pip python3-venv postgresql postgresql-contrib redis-server nginx
   
   # Install system dependencies for WeasyPrint
   sudo apt install -y libpango-1.0-0 libharfbuzz0b libpangocairo-1.0-0 libcairo2
   
   # Clone repository
   git clone https://github.com/yourusername/clinic-backend.git
   cd clinic-backend
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt gunicorn
   
   # Setup PostgreSQL
   sudo -u postgres psql
   CREATE DATABASE clinic_db;
   CREATE USER clinic_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE clinic_db TO clinic_user;
   \q
   
   # Configure environment
   cp .env.example .env
   nano .env  # Edit with production values
   
   # Run migrations
   flask db upgrade
   python init_admin.py
   
   # Test run
   gunicorn -w 4 -b 0.0.0.0:8000 run:app
   ```

3. **Setup Systemd Service**
   ```bash
   sudo nano /etc/systemd/system/clinic-backend.service
   ```
   ```ini
   [Unit]
   Description=Clinic Backend Gunicorn
   After=network.target postgresql.service redis.service
   
   [Service]
   User=ubuntu
   Group=ubuntu
   WorkingDirectory=/home/ubuntu/clinic-backend
   Environment="PATH=/home/ubuntu/clinic-backend/venv/bin"
   ExecStart=/home/ubuntu/clinic-backend/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 run:app
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable clinic-backend
   sudo systemctl start clinic-backend
   ```

4. **Setup Nginx Reverse Proxy**
   ```bash
   sudo nano /etc/nginx/sites-available/clinic-backend
   ```
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
   ```bash
   sudo ln -s /etc/nginx/sites-available/clinic-backend /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

5. **Setup SSL with Let's Encrypt**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

**Cost**: ~$15-50/month depending on instance size

---

### Option 5: DigitalOcean App Platform

**Best for**: Simple PaaS, good pricing

#### Steps

1. **Create app.yaml**
   ```yaml
   name: clinic-backend
   services:
     - name: api
       github:
         repo: yourusername/clinic-backend
         branch: main
       run_command: gunicorn -w 4 -b 0.0.0.0:8080 run:app
       environment_slug: python
       instance_count: 1
       instance_size_slug: basic-xxs
       envs:
         - key: SECRET_KEY
           scope: RUN_TIME
           type: SECRET
         - key: FLASK_ENV
           value: production
         - key: DATABASE_URL
           value: ${db.DATABASE_URL}
           type: SECRET
       http_port: 8080
   
   databases:
     - name: db
       engine: PG
       production: true
       version: "15"
   ```

2. **Deploy**
   - Connect GitHub repo in DigitalOcean dashboard
   - App Platform auto-detects `app.yaml`
   - Creates database and deploys

**Cost**: $5-12/month

---

### Option 6: Google Cloud Run

**Best for**: Serverless, pay-per-use

#### Steps

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.13-slim
   
   WORKDIR /app
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       libpango-1.0-0 libharfbuzz0b libpangocairo-1.0-0 libcairo2 \
       postgresql-client \
       && rm -rf /var/lib/apt/lists/*
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt gunicorn
   
   COPY . .
   
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "run:app"]
   ```

2. **Deploy**
   ```bash
   # Install gcloud CLI
   gcloud builds submit --tag gcr.io/PROJECT-ID/clinic-backend
   gcloud run deploy clinic-backend \
     --image gcr.io/PROJECT-ID/clinic-backend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars FLASK_ENV=production
   ```

**Cost**: Pay-per-request, very cheap for low traffic

---

## Offline Deployment (On-Premises)

### Option 1: Docker Deployment (Recommended)

**Best for**: Easy setup, consistent environment, easy updates

#### Prerequisites
- Docker and Docker Compose installed
- Server with 4GB+ RAM, 50GB+ storage

#### Steps

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.13-slim
   
   WORKDIR /app
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       libpango-1.0-0 libharfbuzz0b libpangocairo-1.0-0 libcairo2 \
       postgresql-client \
       && rm -rf /var/lib/apt/lists/*
   
   # Copy requirements and install Python dependencies
   COPY requirements.txt pyproject.toml ./
   RUN pip install --no-cache-dir -r requirements.txt gunicorn
   
   # Copy application code
   COPY . .
   
   # Expose port
   EXPOSE 8000
   
   # Run migrations and start server
   CMD ["sh", "-c", "flask db upgrade && gunicorn -w 4 -b 0.0.0.0:8000 run:app"]
   ```

2. **Create docker-compose.yml**
   ```yaml
   version: '3.8'
   
   services:
     db:
       image: postgres:15-alpine
       container_name: clinic_db
       environment:
         POSTGRES_DB: clinic_db
         POSTGRES_USER: clinic_user
         POSTGRES_PASSWORD: ${DB_PASSWORD:-secure_password}
       volumes:
         - postgres_data:/var/lib/postgresql/data
       ports:
         - "5432:5432"
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U clinic_user"]
         interval: 10s
         timeout: 5s
         retries: 5
   
     redis:
       image: redis:7-alpine
       container_name: clinic_redis
       ports:
         - "6379:6379"
       volumes:
         - redis_data:/data
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 10s
         timeout: 5s
         retries: 5
   
     backend:
       build: .
       container_name: clinic_backend
       environment:
         SECRET_KEY: ${SECRET_KEY:-change-me-in-production}
         DATABASE_URL: postgresql://clinic_user:${DB_PASSWORD:-secure_password}@db:5432/clinic_db
         REDIS_URL: redis://redis:6379/0
         FLASK_ENV: production
         DICOM_STORAGE_PATH: /app/dicom_files
         THUMBNAIL_STORAGE_PATH: /app/thumbnails
         PDF_REPORTS_PATH: /app/reports
       ports:
         - "8000:8000"
       volumes:
         - ./dicom_files:/app/dicom_files
         - ./thumbnails:/app/thumbnails
         - ./reports:/app/reports
       depends_on:
         db:
           condition: service_healthy
         redis:
           condition: service_healthy
       restart: unless-stopped
   
     nginx:
       image: nginx:alpine
       container_name: clinic_nginx
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf:ro
         - ./ssl:/etc/nginx/ssl:ro
       depends_on:
         - backend
       restart: unless-stopped
   
   volumes:
     postgres_data:
     redis_data:
   ```

3. **Create nginx.conf**
   ```nginx
   events {
       worker_connections 1024;
   }
   
   http {
       upstream backend {
           server backend:8000;
       }
   
       server {
           listen 80;
           server_name localhost;
           
           # Redirect HTTP to HTTPS (optional)
           # return 301 https://$server_name$request_uri;
           
           location / {
               proxy_pass http://backend;
               proxy_set_header Host $host;
               proxy_set_header X-Real-IP $remote_addr;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme;
           }
       }
   
       # HTTPS server (if SSL certificates available)
       # server {
       #     listen 443 ssl;
       #     server_name localhost;
       #     
       #     ssl_certificate /etc/nginx/ssl/cert.pem;
       #     ssl_certificate_key /etc/nginx/ssl/key.pem;
       #     
       #     location / {
       #         proxy_pass http://backend;
       #         proxy_set_header Host $host;
       #         proxy_set_header X-Real-IP $remote_addr;
       #         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       #         proxy_set_header X-Forwarded-Proto $scheme;
       #     }
       # }
   }
   ```

4. **Create .env file**
   ```bash
   SECRET_KEY=your-very-long-random-secret-key-here
   DB_PASSWORD=secure_password_change_me
   ```

5. **Deploy**
   ```bash
   # Build and start all services
   docker-compose up -d
   
   # Initialize database
   docker-compose exec backend flask db upgrade
   docker-compose exec backend python init_admin.py
   
   # View logs
   docker-compose logs -f backend
   
   # Stop services
   docker-compose down
   
   # Update application
   git pull
   docker-compose build backend
   docker-compose up -d
   ```

6. **Access Application**
   - Backend API: http://localhost:8000
   - Through Nginx: http://localhost

**Advantages**:
- Easy updates (just rebuild container)
- Consistent environment
- Easy backup (database volumes)
- Can run on any Linux server

---

### Option 2: Traditional Server Setup

**Best for**: Full control, no Docker dependency

#### Steps

1. **Server Requirements**
   - Ubuntu 22.04 LTS or similar
   - 4GB+ RAM
   - 50GB+ storage
   - Python 3.13
   - PostgreSQL 15+
   - Redis 7+
   - Nginx

2. **Install Dependencies**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y python3.13 python3-pip python3-venv \
       postgresql postgresql-contrib redis-server nginx \
       libpango-1.0-0 libharfbuzz0b libpangocairo-1.0-0 libcairo2
   ```

3. **Setup PostgreSQL**
   ```bash
   sudo -u postgres psql
   CREATE DATABASE clinic_db;
   CREATE USER clinic_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE clinic_db TO clinic_user;
   \q
   ```

4. **Setup Application**
   ```bash
   # Create application user
   sudo useradd -m -s /bin/bash clinic
   sudo su - clinic
   
   # Clone repository
   git clone https://github.com/yourusername/clinic-backend.git
   cd clinic-backend
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt gunicorn
   
   # Configure environment
   cp .env.example .env
   nano .env  # Edit with production values
   
   # Run migrations
   flask db upgrade
   python init_admin.py
   ```

5. **Setup Gunicorn Service**
   ```bash
   sudo nano /etc/systemd/system/clinic-backend.service
   ```
   ```ini
   [Unit]
   Description=Clinic Backend Gunicorn
   After=network.target postgresql.service redis.service
   
   [Service]
   User=clinic
   Group=clinic
   WorkingDirectory=/home/clinic/clinic-backend
   Environment="PATH=/home/clinic/clinic-backend/venv/bin"
   ExecStart=/home/clinic/clinic-backend/venv/bin/gunicorn \
       -w 4 \
       -b 127.0.0.1:8000 \
       --access-logfile /var/log/clinic/access.log \
       --error-logfile /var/log/clinic/error.log \
       run:app
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo mkdir -p /var/log/clinic
   sudo chown clinic:clinic /var/log/clinic
   sudo systemctl daemon-reload
   sudo systemctl enable clinic-backend
   sudo systemctl start clinic-backend
   ```

6. **Setup Nginx**
   ```bash
   sudo nano /etc/nginx/sites-available/clinic-backend
   ```
   ```nginx
   server {
       listen 80;
       server_name clinic.local;  # Change to your domain/IP
       
       client_max_body_size 100M;  # For DICOM file uploads
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       # Static files (if serving directly)
       location /static {
           alias /home/clinic/clinic-backend/static;
       }
   }
   ```
   ```bash
   sudo ln -s /etc/nginx/sites-available/clinic-backend /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

7. **Setup Firewall**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

---

### Option 3: Single Machine Setup

**Best for**: Small clinics, single workstation

#### Steps

1. **Install Everything on One Machine**
   - Windows: Use WSL2 or install PostgreSQL/Redis separately
   - Linux: Follow Option 2 steps
   - macOS: Use Homebrew

2. **Run Application Locally**
   ```bash
   # Development mode
   python run.py
   
   # Or production mode
   gunicorn -w 2 -b 0.0.0.0:5000 run:app
   ```

3. **Access from Network**
   - Find machine IP: `ip addr show` or `ipconfig`
   - Access from other machines: http://192.168.1.100:5000
   - Configure firewall to allow port 5000

**Note**: Not recommended for production, but works for small setups

---

## Pre-Deployment Checklist

### Security
- [ ] Change `SECRET_KEY` to strong random value
- [ ] Change default database passwords
- [ ] Review and restrict firewall rules
- [ ] Enable HTTPS/SSL certificates
- [ ] Set `FLASK_ENV=production`
- [ ] Review CORS settings if needed
- [ ] Disable debug mode
- [ ] Set secure session cookies

### Database
- [ ] Backup existing database (if migrating)
- [ ] Run all migrations: `flask db upgrade`
- [ ] Initialize admin users: `python init_admin.py`
- [ ] Test database connectivity
- [ ] Set up database backups (cron job or cloud backup)

### Application
- [ ] Test all API endpoints
- [ ] Verify file storage paths exist and are writable
- [ ] Check environment variables are set correctly
- [ ] Test DICOM file uploads/downloads
- [ ] Verify Redis connection (if using Celery/SocketIO)
- [ ] Test authentication flow

### Infrastructure
- [ ] Server has sufficient resources (CPU, RAM, disk)
- [ ] Network connectivity tested
- [ ] Domain name configured (if using)
- [ ] SSL certificates installed (for HTTPS)
- [ ] Monitoring/logging configured
- [ ] Backup strategy in place

---

## Post-Deployment Steps

### 1. Verify Deployment
```bash
# Check application is running
curl http://localhost:8000/api/auth/me

# Check database connection
docker-compose exec backend flask db current

# Check logs
docker-compose logs backend
# or
sudo journalctl -u clinic-backend -f
```

### 2. Initialize Admin User
```bash
# If not done during deployment
python init_admin.py
# or
docker-compose exec backend python init_admin.py
```

### 3. Test API Endpoints
- Use Postman collection from `api_doc.txt`
- Test login endpoint
- Test patient creation
- Test appointment creation

### 4. Setup Monitoring

**Option A: Simple Log Monitoring**
```bash
# View application logs
tail -f /var/log/clinic/error.log

# View system logs
sudo journalctl -u clinic-backend -f
```

**Option B: Application Monitoring**
- Use services like Sentry for error tracking
- Use Prometheus + Grafana for metrics
- Use UptimeRobot for uptime monitoring

### 5. Setup Backups

**Database Backup Script** (`backup_db.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/backups/clinic"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Docker deployment
docker-compose exec -T db pg_dump -U clinic_user clinic_db > $BACKUP_DIR/clinic_db_$DATE.sql

# Traditional deployment
pg_dump -U clinic_user clinic_db > $BACKUP_DIR/clinic_db_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "clinic_db_*.sql" -mtime +30 -delete
```

**Setup Cron Job**:
```bash
# Run daily at 2 AM
0 2 * * * /path/to/backup_db.sh
```

### 6. Setup Updates

**Update Script** (`update.sh`):
```bash
#!/bin/bash
cd /path/to/clinic-backend

# Pull latest code
git pull origin main

# Docker deployment
docker-compose build backend
docker-compose up -d backend
docker-compose exec backend flask db upgrade

# Traditional deployment
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
sudo systemctl restart clinic-backend
```

---

## Monitoring & Maintenance

### Health Check Endpoint

Add to your routes:
```python
@bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'database': check_db_connection(),
        'redis': check_redis_connection()
    })
```

### Regular Maintenance Tasks

1. **Weekly**
   - Review error logs
   - Check disk space
   - Verify backups are running

2. **Monthly**
   - Update dependencies: `pip list --outdated`
   - Review security updates
   - Check database size and optimize if needed

3. **Quarterly**
   - Review and update SSL certificates
   - Performance testing
   - Security audit

### Troubleshooting

**Application won't start**
```bash
# Check logs
docker-compose logs backend
# or
sudo journalctl -u clinic-backend -n 50

# Check database connection
flask db current

# Check environment variables
env | grep FLASK
```

**Database connection errors**
```bash
# Test PostgreSQL connection
psql -U clinic_user -d clinic_db -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

**High memory usage**
- Reduce Gunicorn workers: `-w 2` instead of `-w 4`
- Check for memory leaks in application code
- Increase server RAM or use swap

---

## Quick Reference

### Docker Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f backend

# Execute commands
docker-compose exec backend flask db upgrade
docker-compose exec backend python init_admin.py

# Update application
git pull && docker-compose build backend && docker-compose up -d
```

### Systemd Commands
```bash
# Start service
sudo systemctl start clinic-backend

# Stop service
sudo systemctl stop clinic-backend

# Restart service
sudo systemctl restart clinic-backend

# View logs
sudo journalctl -u clinic-backend -f

# Enable on boot
sudo systemctl enable clinic-backend
```

### Database Commands
```bash
# Run migrations
flask db upgrade

# Create migration
flask db migrate -m "description"

# Rollback migration
flask db downgrade

# Check current revision
flask db current
```

---

## Support & Resources

- Flask Documentation: https://flask.palletsprojects.com/
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Docker Documentation: https://docs.docker.com/
- Gunicorn Documentation: https://docs.gunicorn.org/

---

**Last Updated**: 2024-01-08

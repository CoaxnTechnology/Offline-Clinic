# Deploying DICOM API on Bluehost - Complete Guide

## ⚠️ Important Limitations

**Bluehost Shared Hosting:**
- ❌ **No Python/Flask support** (only PHP)
- ❌ **No TCP port access** (DICOM ports 11112, 11113 won't work)
- ❌ **No PostgreSQL** (only MySQL)
- ❌ **No SSH access** (on basic plans)

**Bluehost VPS/Dedicated:**
- ✅ **Full control** (SSH access)
- ✅ **Python/Flask support**
- ✅ **TCP port access** (can configure firewall)
- ✅ **PostgreSQL support** (can install)

---

## 🎯 Solution Options

### Option 1: Bluehost VPS (Recommended)
- Full control, can run Flask + DICOM servers
- Supports TCP ports
- More expensive but works

### Option 2: Hybrid Deployment
- Bluehost: Host static files/docs (if needed)
- VPS (Oracle Cloud Free): Run Flask + DICOM servers
- Both connect to same database

### Option 3: Alternative Hosting
- Use Oracle Cloud Free (better for DICOM)
- Or Railway/Fly.io (easier deployment)

---

## 📋 Option 1: Bluehost VPS Deployment

### Prerequisites

1. **Bluehost VPS Plan** (not shared hosting)
   - VPS Standard or higher
   - Root access required
   - SSH access enabled

2. **Domain** (optional, can use IP)

---

### Step 1: Access Your VPS

**SSH into your Bluehost VPS:**
```bash
ssh root@your-server-ip
# or
ssh root@your-domain.com
```

**Verify access:**
```bash
whoami  # Should show: root
pwd     # Should show: /root
```

---

### Step 2: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.13 (or 3.11+)
sudo apt install python3.13 python3.13-venv python3-pip -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Redis (for Celery)
sudo apt install redis-server -y

# Install Git
sudo apt install git -y

# Install Nginx (for reverse proxy)
sudo apt install nginx -y

# Install other dependencies
sudo apt install build-essential libpq-dev python3-dev -y
```

---

### Step 3: Setup PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE clinic_db;
CREATE USER clinic_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE clinic_db TO clinic_user;
\q
```

**Note the connection string:**
```
postgresql://clinic_user:your_secure_password@localhost:5432/clinic_db
```

---

### Step 4: Deploy Your Application

```bash
# Create application directory
mkdir -p /var/www/clinic-backend
cd /var/www/clinic-backend

# Clone your repository (or upload files)
git clone <your-repo-url> .
# OR upload files via SFTP/SCP

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 5: Configure Environment Variables

```bash
# Create .env file
nano /var/www/clinic-backend/.env
```

**Add:**
```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=<generate-strong-random-key>
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Database
DATABASE_URL=postgresql://clinic_user:your_secure_password@localhost:5432/clinic_db

# Redis
REDIS_URL=redis://localhost:6379/0

# DICOM Configuration
DICOM_STORAGE_PATH=/var/www/clinic-backend/dicom_files
THUMBNAIL_STORAGE_PATH=/var/www/clinic-backend/thumbnails
PDF_REPORTS_PATH=/var/www/clinic-backend/reports
DICOM_MWL_PORT=11112
DICOM_STORAGE_PORT=11113
DICOM_AE_TITLE=STORESCP

# Auto-start DICOM servers
AUTO_START_DICOM=true
```

**Generate SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

### Step 6: Initialize Database

```bash
cd /var/www/clinic-backend
source venv/bin/activate

# Set environment variables
export DATABASE_URL=postgresql://clinic_user:your_secure_password@localhost:5432/clinic_db

# Run migrations
flask db upgrade

# Create admin user
python init_admin.py
```

---

### Step 7: Create Storage Directories

```bash
mkdir -p /var/www/clinic-backend/dicom_files
mkdir -p /var/www/clinic-backend/thumbnails
mkdir -p /var/www/clinic-backend/reports
mkdir -p /var/www/clinic-backend/logs

# Set permissions
chmod 755 /var/www/clinic-backend/dicom_files
chmod 755 /var/www/clinic-backend/thumbnails
chmod 755 /var/www/clinic-backend/reports
```

---

### Step 8: Configure Firewall

```bash
# Install UFW if not installed
sudo apt install ufw -y

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow DICOM ports
sudo ufw allow 11112/tcp
sudo ufw allow 11113/tcp

# Allow Flask port (if not using Nginx)
sudo ufw allow 5000/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

### Step 9: Setup Nginx Reverse Proxy

**Create Nginx configuration:**
```bash
sudo nano /etc/nginx/sites-available/clinic-backend
```

**Add:**
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect HTTP to HTTPS (if you have SSL)
    # return 301 https://$server_name$request_uri;

    # For now, proxy to Flask
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/clinic-backend /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

---

### Step 10: Setup SSL Certificate (Optional but Recommended)

**Using Let's Encrypt:**
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

**Update Nginx config** to use HTTPS (certbot does this automatically).

---

### Step 11: Create Systemd Service

**Create service file:**
```bash
sudo nano /etc/systemd/system/clinic-backend.service
```

**Add:**
```ini
[Unit]
Description=Clinic Backend Flask Application
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/clinic-backend
Environment="PATH=/var/www/clinic-backend/venv/bin"
EnvironmentFile=/var/www/clinic-backend/.env
ExecStart=/var/www/clinic-backend/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 "app:create_app()"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable clinic-backend
sudo systemctl start clinic-backend

# Check status
sudo systemctl status clinic-backend

# View logs
sudo journalctl -u clinic-backend -f
```

---

### Step 12: Test Deployment

**Check Flask is running:**
```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/dicom/server/status
```

**Check via domain:**
```bash
curl http://your-domain.com/health
```

**Check DICOM ports:**
```bash
netstat -tuln | grep -E "11112|11113|5000"
```

---

## 📋 Option 2: Hybrid Deployment (Bluehost + VPS)

### Architecture:
```
Bluehost: Static files/docs (optional)
VPS (Oracle Cloud Free): Flask API + DICOM Servers
Both: Connect to same PostgreSQL database
```

### Steps:

1. **Deploy Flask + DICOM on VPS** (Oracle Cloud Free)
   - Follow Oracle Cloud deployment guide
   - Full TCP port access
   - Free forever

2. **Use Bluehost for:**
   - Domain/DNS management
   - Static documentation (if needed)
   - Email services

3. **Point domain to VPS:**
   - In Bluehost DNS settings
   - Add A record: `@` → VPS IP address
   - Add A record: `www` → VPS IP address

**Advantages:**
- ✅ Free VPS (Oracle Cloud)
- ✅ Use Bluehost domain
- ✅ Full DICOM functionality
- ✅ Cost-effective

---

## 📋 Option 3: Alternative Hosting (Recommended)

### Why Not Bluehost?

**Issues:**
- Shared hosting doesn't support Python/Flask
- No TCP port access for DICOM
- More expensive than free alternatives

**Better Alternatives:**

1. **Oracle Cloud Free Tier** (Best)
   - Always free
   - Full control
   - TCP ports work
   - Better for DICOM

2. **Railway** (Easiest)
   - Free tier available
   - Easy deployment
   - Supports TCP (with limitations)

3. **Fly.io** (Good)
   - Free tier
   - TCP support
   - Global edge network

---

## 🔧 Bluehost VPS Specific Configuration

### If Bluehost Blocks Ports

**Contact Bluehost Support:**
- Request ports 11112 and 11113 to be opened
- Explain it's for DICOM medical imaging
- They may need to configure firewall rules

**Alternative:**
- Use different ports (if allowed)
- Update `.env`:
  ```bash
  DICOM_MWL_PORT=21112
  DICOM_STORAGE_PORT=21113
  ```

### Bluehost File Upload Limits

**Check PHP limits** (if applicable):
```bash
# If using PHP for file uploads
php -i | grep upload_max_filesize
php -i | grep post_max_size
```

**For Flask:**
- File upload limits are in Flask config
- Default: 100MB (configurable)

---

## 🧪 Testing After Deployment

### 1. Test HTTP Endpoints

```bash
# Health check
curl http://your-domain.com/health

# DICOM status
curl http://your-domain.com/api/dicom/server/status
```

### 2. Test DICOM Ports

**From your local machine:**
```bash
# Test MWL port
telnet your-domain.com 11112

# Test Storage port
telnet your-domain.com 11113
```

**Or use nmap:**
```bash
nmap -p 11112,11113 your-domain.com
```

### 3. Test with Postman

**Base URL:** `http://your-domain.com` or `https://your-domain.com`

**Test endpoints:**
- Login: `POST /api/auth/login`
- Get status: `GET /api/dicom/server/status`
- List studies: `GET /api/dicom/studies`

---

## 🔍 Troubleshooting

### Issue: "Port 11112/11113 not accessible"

**Solutions:**
1. Check firewall: `sudo ufw status`
2. Check Bluehost firewall rules
3. Contact Bluehost support to open ports
4. Use alternative ports

### Issue: "Flask app not starting"

**Check logs:**
```bash
sudo journalctl -u clinic-backend -f
```

**Common fixes:**
- Check `.env` file exists
- Verify database connection
- Check Python path in service file

### Issue: "Database connection failed"

**Test connection:**
```bash
psql postgresql://clinic_user:password@localhost:5432/clinic_db
```

**Check PostgreSQL:**
```bash
sudo systemctl status postgresql
```

### Issue: "DICOM servers not starting"

**Check:**
- Ports not in use: `sudo lsof -i :11112`
- Firewall allows ports
- Logs show errors

---

## 📊 Cost Comparison

| Option | Monthly Cost | TCP Ports | Best For |
|--------|-------------|-----------|----------|
| **Bluehost VPS** | $19-59 | ✅ Yes | If you already have Bluehost |
| **Oracle Cloud Free** | $0 | ✅ Yes | Best value |
| **Railway** | $0* | ✅ Limited | Easy deployment |
| **Hybrid (Bluehost + Oracle)** | $0 | ✅ Yes | Use Bluehost domain |

*Within free tier limits

---

## ✅ Recommended Approach

### For DICOM APIs:

**Best Option:** Oracle Cloud Free Tier
- ✅ Always free
- ✅ Full TCP port access
- ✅ Better performance
- ✅ More control

**If you must use Bluehost:**
- Use Bluehost VPS (not shared)
- Follow Option 1 instructions
- Contact support for port access

**Hybrid Approach:**
- Use Bluehost for domain/DNS
- Deploy Flask + DICOM on Oracle Cloud Free
- Point domain to Oracle Cloud VPS

---

## 📝 Summary

**Bluehost Shared Hosting:**
- ❌ Won't work (no Python/Flask support)

**Bluehost VPS:**
- ✅ Can work (follow Option 1)
- ⚠️ May need support to open DICOM ports
- 💰 More expensive than free alternatives

**Recommendation:**
- Use **Oracle Cloud Free Tier** for deployment
- Use **Bluehost** for domain management only
- Best of both worlds: Free hosting + Bluehost domain

---

**Last Updated:** 2024-01-08

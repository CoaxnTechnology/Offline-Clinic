#!/bin/bash
cd /opt/Offline-Clinic
git fetch origin
git checkout dev
git reset --hard origin/dev
source venv/bin/activate
pip install -r requirements.txt --quiet
flask db upgrade
sudo systemctl restart clinic-backend
echo "$(date): Dev deployed" >> /opt/Offline-Clinic/deploy.log


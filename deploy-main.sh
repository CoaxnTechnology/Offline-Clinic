#!/bin/bash
cd /opt/Offline-Clinic
git fetch origin
git checkout main
git reset --hard origin/main
source venv/bin/activate
pip install -r requirements.txt --quiet
flask db upgrade
sudo systemctl restart clinic-backend
echo "$(date): Main deployed" >> /opt/Offline-Clinic/deploy.log


#!/bin/bash
# Backup script for Clinic Backend
# Backs up database and DICOM/report files daily
# Usage: ./backup.sh [backup_directory]

set -e

# Configuration
BACKUP_DIR="${1:-/opt/backups/clinic}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="clinic_backup_${TIMESTAMP}"

# Database configuration (from .env or environment)
DB_NAME="${DB_NAME:-clinic_db}"
DB_USER="${DB_USER:-clinic_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Project directories
PROJECT_ROOT="${PROJECT_ROOT:-/opt/Offline-Clinic}"
DICOM_STORAGE="${DICOM_STORAGE:-${PROJECT_ROOT}/dicom_storage}"
REPORTS_DIR="${REPORTS_DIR:-${PROJECT_ROOT}/reports}"
PRESCRIPTIONS_DIR="${PRESCRIPTIONS_DIR:-${PROJECT_ROOT}/reports/prescriptions}"

# Create backup directory structure
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}/database"
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}/files"

echo "Starting backup: ${BACKUP_NAME}"
echo "Backup directory: ${BACKUP_DIR}/${BACKUP_NAME}"

# Backup PostgreSQL database
echo "Backing up database..."
PGPASSWORD="${DB_PASSWORD}" pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    -F c -f "${BACKUP_DIR}/${BACKUP_NAME}/database/clinic_db.dump" || {
    echo "ERROR: Database backup failed"
    exit 1
}

# Backup DICOM files
if [ -d "${DICOM_STORAGE}" ]; then
    echo "Backing up DICOM files..."
    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/files/dicom_storage.tar.gz" -C "$(dirname "${DICOM_STORAGE}")" "$(basename "${DICOM_STORAGE}")" || {
        echo "WARNING: DICOM backup failed (continuing...)"
    }
else
    echo "WARNING: DICOM storage directory not found: ${DICOM_STORAGE}"
fi

# Backup reports
if [ -d "${REPORTS_DIR}" ]; then
    echo "Backing up reports..."
    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/files/reports.tar.gz" -C "$(dirname "${REPORTS_DIR}")" "$(basename "${REPORTS_DIR}")" || {
        echo "WARNING: Reports backup failed (continuing...)"
    }
else
    echo "WARNING: Reports directory not found: ${REPORTS_DIR}"
fi

# Backup prescriptions
if [ -d "${PRESCRIPTIONS_DIR}" ]; then
    echo "Backing up prescriptions..."
    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/files/prescriptions.tar.gz" -C "$(dirname "${PRESCRIPTIONS_DIR}")" "$(basename "${PRESCRIPTIONS_DIR}")" || {
        echo "WARNING: Prescriptions backup failed (continuing...)"
    }
fi

# Create backup manifest
cat > "${BACKUP_DIR}/${BACKUP_NAME}/manifest.txt" <<EOF
Backup Information
==================
Backup Name: ${BACKUP_NAME}
Timestamp: ${TIMESTAMP}
Date: $(date)

Database:
  Name: ${DB_NAME}
  Host: ${DB_HOST}:${DB_PORT}
  User: ${DB_USER}
  Dump File: database/clinic_db.dump

Files:
  DICOM Storage: files/dicom_storage.tar.gz
  Reports: files/reports.tar.gz
  Prescriptions: files/prescriptions.tar.gz

Backup Size: $(du -sh "${BACKUP_DIR}/${BACKUP_NAME}" | cut -f1)
EOF

# Compress entire backup
echo "Compressing backup..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}" || {
    echo "ERROR: Backup compression failed"
    exit 1
}

# Remove uncompressed directory
rm -rf "${BACKUP_NAME}"

# Cleanup old backups (keep last 30 days)
echo "Cleaning up old backups..."
find "${BACKUP_DIR}" -name "clinic_backup_*.tar.gz" -mtime +30 -delete || {
    echo "WARNING: Cleanup failed (continuing...)"
}

echo "Backup completed successfully: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Backup size: $(du -sh "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)"

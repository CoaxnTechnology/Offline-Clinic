#!/bin/bash
# Restore script for Clinic Backend
# Restores database and files from backup
# Usage: ./restore.sh <backup_file.tar.gz> [--db-only] [--files-only]

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file.tar.gz> [--db-only] [--files-only]"
    exit 1
fi

BACKUP_FILE="$1"
RESTORE_DB=true
RESTORE_FILES=true

if [[ "$*" == *"--db-only"* ]]; then
    RESTORE_FILES=false
fi
if [[ "$*" == *"--files-only"* ]]; then
    RESTORE_DB=false
fi

# Configuration
RESTORE_DIR="/tmp/clinic_restore_$$"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Database configuration
DB_NAME="${DB_NAME:-clinic_db}"
DB_USER="${DB_USER:-clinic_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Project directories
PROJECT_ROOT="${PROJECT_ROOT:-/opt/Offline-Clinic}"
DICOM_STORAGE="${DICOM_STORAGE:-${PROJECT_ROOT}/dicom_storage}"
REPORTS_DIR="${REPORTS_DIR:-${PROJECT_ROOT}/reports}"
PRESCRIPTIONS_DIR="${PRESCRIPTIONS_DIR:-${PROJECT_ROOT}/reports/prescriptions}"

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "Restoring from backup: ${BACKUP_FILE}"
echo "Restore directory: ${RESTORE_DIR}"

# Extract backup
mkdir -p "${RESTORE_DIR}"
echo "Extracting backup..."
tar -xzf "${BACKUP_FILE}" -C "${RESTORE_DIR}" || {
    echo "ERROR: Failed to extract backup"
    exit 1
}

BACKUP_NAME=$(basename "${BACKUP_FILE}" .tar.gz)
RESTORE_PATH="${RESTORE_DIR}/${BACKUP_NAME}"

# Verify backup structure
if [ ! -d "${RESTORE_PATH}" ]; then
    echo "ERROR: Invalid backup structure"
    exit 1
fi

# Restore database
if [ "$RESTORE_DB" = true ]; then
    echo "Restoring database..."
    echo "WARNING: This will overwrite the current database!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled"
        exit 1
    fi
    
    DB_DUMP="${RESTORE_PATH}/database/clinic_db.dump"
    if [ ! -f "${DB_DUMP}" ]; then
        echo "ERROR: Database dump not found in backup"
        exit 1
    fi
    
    # Drop and recreate database (or use pg_restore with --clean)
    echo "Restoring database dump..."
    PGPASSWORD="${DB_PASSWORD}" pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
        -d "${DB_NAME}" --clean --if-exists "${DB_DUMP}" || {
        echo "ERROR: Database restore failed"
        exit 1
    }
    
    echo "Database restored successfully"
fi

# Restore files
if [ "$RESTORE_FILES" = true ]; then
    echo "Restoring files..."
    
    # Restore DICOM files
    if [ -f "${RESTORE_PATH}/files/dicom_storage.tar.gz" ]; then
        echo "Restoring DICOM files..."
        mkdir -p "$(dirname "${DICOM_STORAGE}")"
        tar -xzf "${RESTORE_PATH}/files/dicom_storage.tar.gz" -C "$(dirname "${DICOM_STORAGE}")" || {
            echo "WARNING: DICOM restore failed (continuing...)"
        }
    fi
    
    # Restore reports
    if [ -f "${RESTORE_PATH}/files/reports.tar.gz" ]; then
        echo "Restoring reports..."
        mkdir -p "$(dirname "${REPORTS_DIR}")"
        tar -xzf "${RESTORE_PATH}/files/reports.tar.gz" -C "$(dirname "${REPORTS_DIR}")" || {
            echo "WARNING: Reports restore failed (continuing...)"
        }
    fi
    
    # Restore prescriptions
    if [ -f "${RESTORE_PATH}/files/prescriptions.tar.gz" ]; then
        echo "Restoring prescriptions..."
        mkdir -p "$(dirname "${PRESCRIPTIONS_DIR}")"
        tar -xzf "${RESTORE_PATH}/files/prescriptions.tar.gz" -C "$(dirname "${PRESCRIPTIONS_DIR}")" || {
            echo "WARNING: Prescriptions restore failed (continuing...)"
        }
    fi
    
    echo "Files restored successfully"
fi

# Cleanup
rm -rf "${RESTORE_DIR}"

echo "Restore completed successfully"
echo ""
echo "Next steps:"
echo "1. Restart the Flask application"
echo "2. Verify data integrity"
echo "3. Check application logs"

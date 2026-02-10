#!/bin/bash

# Script to update production server environment
# This ensures AUTO_START_DICOM=false is set on the server

echo "Updating production environment variables..."

# Add AUTO_START_DICOM=false to .env if not present
if ! grep -q "AUTO_START_DICOM" .env; then
    echo "AUTO_START_DICOM=false" >> .env
    echo "Added AUTO_START_DICOM=false to .env"
else
    echo "AUTO_START_DICOM already set in .env"
fi

echo "Environment update complete!"
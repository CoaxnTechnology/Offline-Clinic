#!/usr/bin/env bash
# Check DICOM SCP logs and write SCP-related lines to logs/dicom_scp_report.txt
# Run from project root: ./scripts/check_dicom_scp_logs.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOGS_DIR="$PROJECT_ROOT/logs"
DICOM_LOG="$LOGS_DIR/dicom.log"
APP_LOG="$LOGS_DIR/app.log"
REPORT="$LOGS_DIR/dicom_scp_report.txt"

mkdir -p "$LOGS_DIR"

# Patterns that indicate SCP (C-STORE) activity or errors
PATTERNS="Received DICOM image|Error storing DICOM image|handle_store|C-STORE|STORESCP|Duplicate DICOM|Missing required DICOM metadata|Storage quota|DICOM logging initialized|dicom_service"

{
  echo "=== DICOM SCP log report ==="
  echo "Generated: $(date -Iseconds)"
  echo ""

  if [ -f "$DICOM_LOG" ]; then
    echo "--- From $DICOM_LOG ---"
    grep -E "$PATTERNS" "$DICOM_LOG" 2>/dev/null || true
    echo ""
  else
    echo "--- $DICOM_LOG not found (no DICOM log yet) ---"
    echo ""
  fi

  if [ -f "$APP_LOG" ]; then
    echo "--- From $APP_LOG (DICOM/SCP lines only) ---"
    grep -E "$PATTERNS" "$APP_LOG" 2>/dev/null || true
  else
    echo "--- $APP_LOG not found ---"
  fi
} > "$REPORT"

echo "Report written to: $REPORT"
cat "$REPORT"

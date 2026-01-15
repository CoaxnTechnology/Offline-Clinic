#!/bin/bash
# Start all services for remote testing with Tunisia ultrasound machine
# Usage: ./start_remote_testing.sh

echo "=========================================="
echo "Starting Remote Testing Setup"
echo "For Tunisia Ultrasound Machine"
echo "=========================================="

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed"
    echo "Install from: https://ngrok.com/download"
    echo "Or: brew install ngrok"
    exit 1
fi

# Check if Redis is running
if ! redis-cli ping &> /dev/null; then
    echo "⚠️  Redis is not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

echo ""
echo "Starting services..."
echo ""

# Start Flask server in background
echo "1. Starting Flask server..."
cd "$(dirname "$0")"
uv run flask run --host=0.0.0.0 --port=5000 > flask.log 2>&1 &
FLASK_PID=$!
echo "   ✓ Flask running (PID: $FLASK_PID)"
sleep 3

# Start DICOM listener in background
echo "2. Starting DICOM listener..."
python dicom_listener.py > dicom.log 2>&1 &
DICOM_PID=$!
echo "   ✓ DICOM listener running (PID: $DICOM_PID)"
sleep 2

echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Start ngrok tunnels in separate terminals:"
echo ""
echo "   Terminal 1 - MWL Tunnel:"
echo "   ngrok tcp 11112"
echo ""
echo "   Terminal 2 - Storage Tunnel:"
echo "   ngrok tcp 11113"
echo ""
echo "   Terminal 3 - HTTP Tunnel (for Postman):"
echo "   ngrok http 5000"
echo ""
echo "2. Note the ngrok addresses from each terminal"
echo ""
echo "3. Share MWL and Storage addresses with Tunisia team"
echo ""
echo "4. Configure ultrasound machine with ngrok addresses"
echo ""
echo "5. Test via Postman using ngrok HTTP URL"
echo ""
echo "=========================================="
echo "Services Running:"
echo "  Flask: http://localhost:5000"
echo "  DICOM MWL: localhost:11112"
echo "  DICOM Storage: localhost:11113"
echo ""
echo "To stop services:"
echo "  kill $FLASK_PID $DICOM_PID"
echo "=========================================="

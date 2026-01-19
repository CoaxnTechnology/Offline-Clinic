#!/bin/bash
# Start ngrok tunnels for remote DICOM testing
# Usage: ./start_ngrok_tunnels.sh

echo "=========================================="
echo "Starting ngrok Tunnels for Remote Testing"
echo "=========================================="

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "Error: ngrok is not installed"
    echo "Install from: https://ngrok.com/download"
    echo "Or: brew install ngrok (macOS)"
    exit 1
fi

# Check if ngrok is authenticated
if [ ! -f ~/.ngrok2/ngrok.yml ] && [ ! -f ~/.config/ngrok/ngrok.yml ]; then
    echo "Warning: ngrok may not be authenticated"
    echo "Run: ngrok config add-authtoken YOUR_TOKEN"
    echo ""
fi

echo ""
echo "Starting tunnels..."
echo ""
echo "Terminal 1: MWL Tunnel (Port 11112)"
echo "Command: ngrok tcp 11112"
echo ""
echo "Terminal 2: Storage Tunnel (Port 11113)"
echo "Command: ngrok tcp 11113"
echo ""
echo "Terminal 3: HTTP Tunnel for API (Port 5000)"
echo "Command: ngrok http 5000"
echo ""
echo "=========================================="
echo "IMPORTANT:"
echo "1. Start Flask server first: uv run flask run --host=0.0.0.0"
echo "2. Start DICOM servers: python dicom_listener.py"
echo "3. Run ngrok commands in separate terminals"
echo "4. Note the public URLs from ngrok"
echo "5. Configure ultrasound machine with ngrok URLs"
echo "=========================================="
echo ""

# Option to start tunnels automatically (requires multiple terminals)
read -p "Do you want to start tunnels automatically? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting MWL tunnel..."
    gnome-terminal -- ngrok tcp 11112 &
    sleep 2
    
    echo "Starting Storage tunnel..."
    gnome-terminal -- ngrok tcp 11113 &
    sleep 2
    
    echo "Starting HTTP tunnel..."
    gnome-terminal -- ngrok http 5000 &
    
    echo ""
    echo "Tunnels started in separate windows"
    echo "Check each window for public URLs"
else
    echo ""
    echo "Run these commands manually in separate terminals:"
    echo ""
    echo "Terminal 1: ngrok tcp 11112"
    echo "Terminal 2: ngrok tcp 11113"
    echo "Terminal 3: ngrok http 5000"
fi

from flask import Flask, request
import subprocess
import hmac
import hashlib
import os

app = Flask(__name__)
WEBHOOK_SECRET = WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")


@app.route('/webhook', methods=['POST'])
def webhook():
    # Verify signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        return 'Invalid signature', 403

    payload = request.json
    ref = payload.get('ref', '')

    if ref == 'refs/heads/main':
        # Production deployment
        subprocess.Popen(['/opt/Offline-Clinic/deploy-main.sh'])
        return 'Deploying main', 200
    elif ref == 'refs/heads/dev':
        # Dev/testing deployment
        subprocess.Popen(['/opt/Offline-Clinic/deploy-dev.sh'])
        return 'Deploying dev', 200

    return 'Ignored', 200

def verify_signature(payload, signature):
    if not signature:
        return False
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

if __name__ == '__main__':
    app.run(port=9000)


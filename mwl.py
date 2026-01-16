import os
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from flask import Flask, render_template_string, request, jsonify
import webbrowser
from pynetdicom import AE, evt, debug_logger
from pynetdicom.sop_class import Verification
from pydicom import Dataset
from pydicom.uid import generate_uid, ImplicitVRLittleEndian, ExplicitVRLittleEndian, JPEGBaseline8Bit
from PIL import Image
import numpy as np
import logging
from datetime import datetime
import socket
import io
import base64

# Setup logging
debug_logger()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                    handlers=[logging.FileHandler("clinic.log"), logging.StreamHandler()])

# ================= STATIC PATIENT DATA =================
PATIENTS = [
    {
        'patient_id': 'PT001',
        'name': 'Priya Sharma',
        'age': '28',
        'gender': 'F',
        'study': 'Abdominal Ultrasound',
        'accession': 'ACC001',
        'scheduled_time': '20260103_1400',
        'sent': False
    },
    {
        'patient_id': 'PT002',
        'name': 'Rahul Patel',
        'age': '45',
        'gender': 'M',
        'study': 'Thyroid Ultrasound',
        'accession': 'ACC002',
        'scheduled_time': '20260103_1500',
        'sent': False
    }
]

# Received data
RECEIVED_IMAGES = {}
RECEIVED_MEASUREMENTS = {}

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Clinic PACS Test System</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 10px; text-align: center; }
        .patients { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin: 20px 0; }
        .patient-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .patient-card.sent { background: #d4edda; border: 2px solid #28a745; }
        .btn { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .btn:hover { background: #0056b3; }
        .btn-success { background: #28a745; }
        .btn-success:hover { background: #218838; }
        .results { background: white; padding: 20px; border-radius: 10px; margin: 20px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .image-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .image-card { text-align: center; }
        .thumbnail { max-width: 180px; max-height: 180px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .measurements { background: #e9ecef; padding: 15px; border-radius: 5px; margin: 10px 0; font-family: monospace; }
        .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.waiting { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Clinic PACS Test System</h1>
            <p>Receptionist → Doctor → Auto Results</p>
        </div>
        
        <h2>📋 Patient Worklist</h2>
        <div class="patients">
            {% for patient in patients %}
            <div class="patient-card {% if patient.sent %}sent{% endif %}">
                <h3>{{ patient.name }}</h3>
                <p><strong>ID:</strong> {{ patient.patient_id }} | <strong>Age:</strong> {{ patient.age }} {{ patient.gender }}</p>
                <p><strong>Study:</strong> {{ patient.study }} | <strong>Time:</strong> {{ patient.scheduled_time }}</p>
                <p><strong>Accession:</strong> {{ patient.accession }}</p>
                <button class="btn {% if patient.sent %}btn-success{% else %}btn{% endif %}" 
                        onclick="sendMWL('{{ patient.patient_id }}')">
                    {% if patient.sent %}✅ SENT{% else %}📤 Send to Machine{% endif %}
                </button>
                <div class="status {% if patient.sent %}success{% else %}waiting{% endif %}">
                    {% if patient.sent %}Sent - Ready on machine{% else %}Waiting...{% endif %}
                </div>
            </div>
            {% endfor %}
        </div>

        <h2>📊 Results from Machine</h2>
        <div class="results">
            {% if received_images %}
            <h3>🖼️ Images ({{ received_images|length }})</h3>
            <div class="image-grid">
                {% for img_id, img_data in received_images.items() %}
                <div class="image-card">
                    <h4>{{ img_data.patient }} - {{ img_data.body_part }}</h4>
                    <p>Study: {{ img_data.study_date }}</p>
                    {% if img_data.thumbnail %}
                    <img src="data:image/jpeg;base64,{{ img_data.thumbnail }}" class="thumbnail">
                    {% endif %}
                    <p><em>{{ img_data.modality }} | {{ img_data.manufacturer }}</em></p>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="status waiting">⏳ Waiting for images...</div>
            {% endif %}

            {% if received_measurements %}
            <h3>📏 Measurements</h3>
            {% for study, meas in received_measurements.items() %}
            <div class="measurements">
                <h4>{{ meas.patient }} - {{ meas.study_type }}</h4>
                <pre>{{ meas.measurements }}</pre>
                <p><em>Received: {{ meas.time }}</em></p>
            </div>
            {% endfor %}
            {% endif %}
        </div>

        <div style="text-align: center; margin-top: 30px; padding: 20px; background: #e9ecef; border-radius: 10px;">
            <h3>🧪 TEST STEPS</h3>
            <ol>
                <li>Click "Send to Machine" for a patient</li>
                <li>On ultrasound machine → Worklist → Search (blank fields, today date)</li>
                <li>Select patient → Scan → Send</li>
                <li>Images & measurements appear here automatically</li>
            </ol>
        </div>
    </div>

    <script>
        async function sendMWL(patientId) {
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = 'Sending...';
            try {
                const response = await fetch('/send_mwl', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({patient_id: patientId})
                });
                const result = await response.json();
                if (result.success) {
                    location.reload();
                }
            } catch (e) {
                alert('Error: ' + e.message);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, 
                                patients=PATIENTS, 
                                received_images=RECEIVED_IMAGES,
                                received_measurements=RECEIVED_MEASUREMENTS)

@app.route('/send_mwl', methods=['POST'])
def send_mwl():
    data = request.json
    patient_id = data.get('patient_id')
    for patient in PATIENTS:
        if patient['patient_id'] == patient_id:
            patient['sent'] = True
            logging.info(f"MWL sent for {patient['name']} ({patient_id})")
            return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Not found'})

def save_thumbnail(ds):
    try:
        # Handle compressed data (JPEG Baseline from Samsung)
        if ds.file_meta.TransferSyntaxUID.is_compressed:
            ds.decompress()  # Decompress to raw pixel data
        
        pixel_data = ds.pixel_array
        
        # Take first frame for multiframe (cine loops)
        if pixel_data.ndim >= 3:
            if pixel_data.shape[0] > 1:  # Multiframe
                pixel_data = pixel_data[0]
            if pixel_data.ndim == 3 and pixel_data.shape[-1] == 3:  # RGB
                pixel_data = np.mean(pixel_data, axis=-1)
        
        # Normalize to 8-bit
        p_min, p_max = pixel_data.min(), pixel_data.max()
        if p_max > p_min:
            pixel_data = np.uint8(255 * (pixel_data - p_min) / (p_max - p_min))
        else:
            pixel_data = np.uint8(pixel_data)
        
        img = Image.fromarray(pixel_data).convert('RGB')
        img.thumbnail((200, 200))
        
        bio = io.BytesIO()
        img.save(bio, 'JPEG')
        base64_str = base64.b64encode(bio.getvalue()).decode()
        
        RECEIVED_IMAGES[ds.SOPInstanceUID] = {
            'patient': str(getattr(ds, 'PatientName', 'Unknown')),
            'study_date': getattr(ds, 'StudyDate', 'Unknown'),
            'body_part': getattr(ds, 'BodyPartExamined', 'Unknown'),
            'modality': getattr(ds, 'Modality', 'Unknown'),
            'manufacturer': getattr(ds, 'Manufacturer', 'Unknown'),
            'thumbnail': base64_str
        }
    except Exception as e:
        logging.warning(f"Thumbnail generation failed: {e}")

def handle_mwl_find(event):
    identifier = event.identifier
    if identifier is None:
        yield 0xC000, None
        return

    query_date = getattr(identifier, 'ScheduledProcedureStepStartDate', None)
    modality = None
    if hasattr(identifier, 'ScheduledProcedureStepSequence') and len(identifier.ScheduledProcedureStepSequence) > 0:
        sps = identifier.ScheduledProcedureStepSequence[0]
        modality = getattr(sps, 'Modality', None)

    for patient in PATIENTS:
        if not patient['sent']:
            continue
        if query_date and patient['scheduled_time'][:8] != query_date:
            continue
        if modality and modality != 'US':
            continue

        ds = Dataset()
        ds.PatientName = patient['name']
        ds.PatientID = patient['patient_id']
        ds.PatientBirthDate = ''
        ds.PatientSex = patient['gender']
        ds.AccessionNumber = patient['accession']
        ds.RequestedProcedureDescription = patient['study']
        ds.StudyInstanceUID = generate_uid()

        ds.ScheduledProcedureStepSequence = [Dataset()]
        sps_item = ds.ScheduledProcedureStepSequence[0]
        sps_item.ScheduledProcedureStepDescription = patient['study']
        sps_item.ScheduledProcedureStepStartDate = patient['scheduled_time'][:8]
        sps_item.ScheduledProcedureStepStartTime = patient['scheduled_time'][9:] or '0900'
        sps_item.Modality = 'US'
        sps_item.ScheduledPerformingPhysicianName = ''

        yield 0xFF00, ds

    yield 0x0000, None

def handle_store(event):
    ds = event.dataset
    ds.file_meta = event.file_meta
    sop_uid = ds.SOPInstanceUID
    os.makedirs("./received", exist_ok=True)
    ds.save_as(f"./received/{sop_uid}.dcm", write_like_original=False)
    save_thumbnail(ds)

    measurements_text = "Liver: 12.5 cm | Gallbladder: Normal | Kidneys: Normal"
    RECEIVED_MEASUREMENTS[sop_uid] = {
        'patient': str(getattr(ds, 'PatientName', 'Unknown')),
        'study_type': getattr(ds, 'StudyDescription', 'Ultrasound'),
        'measurements': measurements_text,
        'time': datetime.now().strftime('%H:%M:%S')
    }
    return 0x0000

def start_dicom_servers():
    def mwl_server():
        ae = AE(ae_title='STORESCP')
        ae.require_called_aet = False
        ts = [ImplicitVRLittleEndian, ExplicitVRLittleEndian]
        ae.add_supported_context('1.2.840.10008.5.1.4.31', ts)
        ae.add_supported_context(Verification, ts)
        ae.start_server(('0.0.0.0', 11112), block=True, evt_handlers=[(evt.EVT_C_FIND, handle_mwl_find)])

    def storage_server():
        ae = AE(ae_title='STORESCP')
        ae.require_called_aet = False
        
        ts = [
            JPEGBaseline8Bit,
            '1.2.840.10008.1.2.4.51',
            '1.2.840.10008.1.2.4.57',
            '1.2.840.10008.1.2.4.70',
            ImplicitVRLittleEndian,
            ExplicitVRLittleEndian,
            '1.2.840.10008.1.2.2',
        ]
        
        ae.add_supported_context('1.2.840.10008.5.1.4.1.1.6.1', ts)   # US Single-frame
        ae.add_supported_context('1.2.840.10008.5.1.4.1.1.3.1', ts)   # US Multi-frame
        
        ae.add_supported_context(Verification, ts)
        
        ae.start_server(('0.0.0.0', 11113), block=True, evt_handlers=[(evt.EVT_C_STORE, handle_store)])

    threading.Thread(target=mwl_server, daemon=True).start()
    threading.Thread(target=storage_server, daemon=True).start()

# GUI
root = tk.Tk()
root.title("Clinic PACS Test System")
root.geometry("800x600")

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def start_system():
    ip = get_ip()
    status_label.config(text=f"Running | IP: {ip} | MWL:11112 | Storage:11113")
    start_dicom_servers()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, use_reloader=False), daemon=True).start()
    webbrowser.open(f'http://{ip}:5000')
    log_text.insert(tk.END, f"System started\nWebsite: http://{ip}:5000\nMWL Port: 11112 | Storage Port: 11113\nAE Title: STORESCP\n\n")

tk.Label(root, text="Clinic PACS Test System", font=("Arial", 16, "bold")).pack(pady=20)
tk.Label(root, text=f"PC IP: {get_ip()}", font=("Arial", 14, "bold"), fg="green").pack(pady=10)

tk.Button(root, text="START SYSTEM", command=start_system,
          bg="#28a745", fg="white", font=14, height=2, width=40).pack(pady=30)

status_label = tk.Label(root, text="Ready", fg="blue")
status_label.pack(pady=10)

log_text = scrolledtext.ScrolledText(root, height=20)
log_text.pack(padx=20, pady=10, fill="both", expand=True)

root.mainloop()

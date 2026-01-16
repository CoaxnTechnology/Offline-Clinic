# MWL.py - DICOM Modality Worklist (MWL) Server Explanation

## Overview

`mwl.py` is a **DICOM Modality Worklist (MWL) server** that acts as a bridge between your clinic's reception system and ultrasound machines. It implements the DICOM MWL protocol to provide patient worklists to imaging devices.

## What is MWL (Modality Worklist)?

MWL is a DICOM service that allows imaging devices (like ultrasound machines) to query a server for scheduled patient procedures. Instead of manually entering patient data on the machine, the machine queries the MWL server and gets a list of scheduled patients.

## Architecture

The system consists of **3 main components**:

1. **Flask Web Server** (Port 5000) - Web interface for receptionists
2. **MWL Server** (Port 11112) - DICOM C-FIND service for worklist queries
3. **Storage Server** (Port 11113) - DICOM C-STORE service to receive images

## Components Breakdown

### 1. Static Patient Data (Lines 24-46)

```python
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
    ...
]
```

- **Purpose**: Hardcoded list of scheduled patients
- **Fields**:
  - `patient_id`: Unique patient identifier
  - `name`: Patient name
  - `age`, `gender`: Demographics
  - `study`: Type of examination
  - `accession`: Accession number (unique study identifier)
  - `scheduled_time`: Date and time (format: YYYYMMDD_HHMM)
  - `sent`: Flag indicating if MWL was sent to machine

### 2. Flask Web Interface (Lines 54-172)

**Purpose**: Provides a web-based UI for receptionists to manage patient worklists.

**Features**:
- Display list of scheduled patients
- "Send to Machine" button for each patient
- Visual status indicators (sent/not sent)
- Display received images and measurements
- Auto-refresh after sending MWL

**Routes**:
- `GET /` - Main dashboard showing patients and results
- `POST /send_mwl` - Mark patient as sent to machine

### 3. MWL Server (Lines 232-271)

**Function**: `handle_mwl_find(event)`

**How it works**:
1. Ultrasound machine sends a C-FIND request with query parameters
2. Server filters patients based on:
   - Date match (if query includes date)
   - Modality match (must be 'US' for ultrasound)
   - Only patients marked as `sent=True`
3. Returns matching patients as DICOM datasets

**DICOM Fields Returned**:
- PatientName
- PatientID
- PatientSex
- AccessionNumber
- StudyInstanceUID (generated)
- ScheduledProcedureStepSequence (with date, time, modality)

**Port**: 11112

### 4. Storage Server (Lines 273-288)

**Function**: `handle_store(event)`

**Purpose**: Receives DICOM images sent from the ultrasound machine after scanning.

**What it does**:
1. Receives DICOM image via C-STORE
2. Saves file to `./received/` directory
3. Generates thumbnail for web display
4. Stores measurement data (currently hardcoded)

**Port**: 11113

### 5. Thumbnail Generation (Lines 192-230)

**Function**: `save_thumbnail(ds)`

**Process**:
1. Decompresses DICOM pixel data if compressed
2. Handles multiframe images (takes first frame)
3. Converts to grayscale if RGB
4. Normalizes to 8-bit
5. Creates thumbnail (200x200px)
6. Converts to base64 for web display

### 6. GUI Launcher (Lines 323-358)

**Purpose**: Tkinter GUI to start the system.

**Features**:
- Shows PC IP address
- "START SYSTEM" button
- Status display
- Log output area
- Auto-opens web browser

## Workflow

### Complete Flow:

```
1. Receptionist opens web interface (http://PC_IP:5000)
   ↓
2. Receptionist clicks "Send to Machine" for a patient
   ↓
3. Patient marked as sent=True in PATIENTS list
   ↓
4. Doctor/Technician goes to ultrasound machine
   ↓
5. Machine queries MWL server (port 11112) for worklist
   ↓
6. MWL server returns patient(s) marked as sent
   ↓
7. Machine displays worklist, doctor selects patient
   ↓
8. Doctor performs scan on machine
   ↓
9. Machine sends DICOM images to Storage server (port 11113)
   ↓
10. Storage server saves images and generates thumbnails
   ↓
11. Web interface automatically shows received images
```

## Key DICOM Concepts

### AE Title
- **Value**: `STORESCP`
- **Purpose**: Application Entity title - identifies this server to DICOM devices

### Transfer Syntaxes Supported
- Implicit VR Little Endian (standard)
- Explicit VR Little Endian
- JPEG Baseline 8-bit (for compressed images from Samsung machines)

### SOP Classes Supported
- **MWL**: `1.2.840.10008.5.1.4.31` (Modality Worklist)
- **Storage**: 
  - `1.2.840.10008.5.1.4.1.1.6.1` (US Single-frame)
  - `1.2.840.10008.5.1.4.1.1.3.1` (US Multi-frame)

## Configuration

### Ports
- **Web Server**: 5000
- **MWL Server**: 11112
- **Storage Server**: 11113

### Network
- Binds to `0.0.0.0` (all interfaces)
- Auto-detects local IP address
- Accessible from network (not just localhost)

### Directories
- **Received Images**: `./received/` (created automatically)
- **Logs**: `clinic.log`

## Usage

### Starting the System

```bash
python3 mwl.py
```

1. GUI window opens
2. Click "START SYSTEM" button
3. Web browser opens automatically
4. System is ready

### On Ultrasound Machine

1. Go to Worklist menu
2. Configure MWL server:
   - **IP**: PC's IP address
   - **Port**: 11112
   - **AE Title**: STORESCP
3. Search worklist (leave fields blank, use today's date)
4. Select patient from list
5. Perform scan
6. Send images (configured to send to same PC, port 11113)

## Current Limitations

1. **Hardcoded Patients**: Patient list is static, not from database
2. **Hardcoded Measurements**: Measurement data is fake/static
3. **No Database Integration**: Doesn't connect to your PostgreSQL database
4. **No Authentication**: Web interface has no login
5. **Single Machine**: Designed for one ultrasound machine

## Integration Opportunities

To integrate with your existing backend:

1. **Replace Static PATIENTS** with database queries:
   ```python
   from app.models import Patient, Appointment
   # Query appointments for today
   ```

2. **Store Received Images** in database:
   ```python
   # Create DICOM Study/Series models
   # Link to Patient via PatientID
   ```

3. **Real Measurements**: Parse DICOM Structured Reports (SR) for actual measurements

4. **Authentication**: Add Flask-Login for web interface

5. **Multiple Machines**: Support multiple AE Titles/ports

## Dependencies

- `pynetdicom` - DICOM networking
- `pydicom` - DICOM file handling
- `Flask` - Web server
- `PIL/Pillow` - Image processing
- `numpy` - Array operations
- `tkinter` - GUI (usually included with Python)

## Security Considerations

⚠️ **Current State**: No security implemented
- No authentication
- No encryption
- Accessible from entire network
- No input validation

**Recommendations**:
- Add authentication to web interface
- Use VPN or firewall rules
- Validate DICOM data
- Rate limiting for DICOM servers

## Testing

The system includes test instructions in the web interface:
1. Click "Send to Machine" for a patient
2. On ultrasound machine → Worklist → Search
3. Select patient → Scan → Send
4. Images appear automatically

## Files Generated

- `./received/*.dcm` - Received DICOM images
- `clinic.log` - System logs

## Summary

`mwl.py` is a **standalone DICOM MWL server** that:
- ✅ Provides worklist to ultrasound machines
- ✅ Receives DICOM images from machines
- ✅ Shows web interface for receptionists
- ✅ Generates thumbnails automatically
- ❌ Not integrated with your PostgreSQL database
- ❌ Uses hardcoded patient data
- ❌ No authentication/security

**Next Steps**: Integrate with your `Patient` and `Appointment` models to make it production-ready!

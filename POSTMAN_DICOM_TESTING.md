# Testing DICOM APIs with Postman (Without Ultrasound Machine)

Complete guide to test all DICOM API endpoints using Postman, even without a physical DICOM device.

---

## ✅ What You CAN Test Without a Machine

**All HTTP endpoints work perfectly:**
- ✅ Server management (start/stop/status)
- ✅ List studies, images, measurements
- ✅ Get study/image details
- ✅ Download DICOM files
- ✅ Get thumbnails
- ✅ Send MWL for appointments
- ✅ Patient studies

**What requires a DICOM device:**
- ❌ MWL queries from device (but you can test MWL via API)
- ❌ C-STORE image reception (but you can upload test files)

---

## 🚀 Quick Start

### Step 1: Start Your Backend

```bash
cd /home/raza/Projects/Clinic/backend

# Start Flask (DICOM servers start automatically)
python run.py
# OR
uv run flask run --host=0.0.0.0 --port=5000
```

**Verify it's running:**
```bash
curl http://localhost:5000/health
```

### Step 2: Login and Get Session Cookie

**Request:**
```http
POST http://localhost:5000/api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**Save the session cookie** from response headers (you'll need it for all requests).

---

## 📋 Complete Postman Testing Guide

### 1. Authentication

#### Login
```http
POST http://localhost:5000/api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**Save:** Copy the `session` cookie from response headers.

---

### 2. DICOM Server Management

#### Get Server Status
```http
GET http://localhost:5000/api/dicom/server/status
Cookie: session=<your-session-cookie>
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "mwl_server_running": true,
    "storage_server_running": true,
    "mwl_port": 11112,
    "storage_port": 11113,
    "ae_title": "STORESCP",
    "mwl_port_open": true,
    "storage_port_open": true
  }
}
```

#### Start DICOM Servers
```http
POST http://localhost:5000/api/dicom/server/start
Cookie: session=<your-session-cookie>
```

**Expected Response:**
```json
{
  "success": true,
  "message": "DICOM servers started successfully",
  "data": {
    "mwl_server_running": true,
    "storage_server_running": true
  }
}
```

#### Stop DICOM Servers
```http
POST http://localhost:5000/api/dicom/server/stop
Cookie: session=<your-session-cookie>
```

---

### 3. DICOM Studies

#### List All Studies
```http
GET http://localhost:5000/api/dicom/studies?page=1&limit=20
Cookie: session=<your-session-cookie>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `patient_id`: Filter by patient ID (optional)
- `study_date`: Filter by date YYYY-MM-DD (optional)
- `accession_number`: Filter by accession number (optional)

**Example:**
```http
GET http://localhost:5000/api/dicom/studies?patient_id=P001&page=1&limit=10
Cookie: session=<your-session-cookie>
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "studies": [
      {
        "study_instance_uid": "1.2.3.4.5",
        "patient_id": "P001",
        "patient_name": "John Doe",
        "study_date": "2024-01-08",
        "study_description": "Ultrasound",
        "modality": "US",
        "image_count": 5
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 1,
      "pages": 1
    }
  }
}
```

#### Get Study Details
```http
GET http://localhost:5000/api/dicom/studies/<study_instance_uid>
Cookie: session=<your-session-cookie>
```

**Example:**
```http
GET http://localhost:5000/api/dicom/studies/1.2.840.113619.2.55.3.1234567890.1234567890123.1
Cookie: session=<your-session-cookie>
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "study_instance_uid": "1.2.3.4.5",
    "patient": {
      "id": "P001",
      "name": "John Doe"
    },
    "series": [
      {
        "series_instance_uid": "1.2.3.4.5.1",
        "modality": "US",
        "series_description": "Abdomen",
        "image_count": 5
      }
    ],
    "study_date": "2024-01-08",
    "study_description": "Ultrasound"
  }
}
```

---

### 4. DICOM Images

#### List All Images
```http
GET http://localhost:5000/api/dicom/images?page=1&limit=20
Cookie: session=<your-session-cookie>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `patient_id`: Filter by patient ID (optional)
- `study_instance_uid`: Filter by study UID (optional)
- `series_instance_uid`: Filter by series UID (optional)
- `modality`: Filter by modality (e.g., "US") (optional)

**Example:**
```http
GET http://localhost:5000/api/dicom/images?modality=US&patient_id=P001&page=1&limit=10
Cookie: session=<your-session-cookie>
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "images": [
      {
        "id": 1,
        "sop_instance_uid": "1.2.3.4.5.1",
        "patient_id": "P001",
        "patient_name": "John Doe",
        "study_date": "2024-01-08",
        "modality": "US",
        "series_description": "Abdomen",
        "has_thumbnail": true
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 5,
      "pages": 1
    }
  }
}
```

#### Get Image Details
```http
GET http://localhost:5000/api/dicom/images/<image_id>
Cookie: session=<your-session-cookie>
```

**Example:**
```http
GET http://localhost:5000/api/dicom/images/1
Cookie: session=<your-session-cookie>
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "sop_instance_uid": "1.2.3.4.5.1",
    "study_instance_uid": "1.2.3.4.5",
    "series_instance_uid": "1.2.3.4.5.1",
    "patient_id": "P001",
    "patient_name": "John Doe",
    "patient_birth_date": "1990-01-01",
    "patient_sex": "M",
    "study_date": "2024-01-08",
    "modality": "US",
    "series_description": "Abdomen",
    "file_path": "dicom_files/1.2.3.4.5.1.dcm",
    "thumbnail_path": "thumbnails/1.2.3.4.5.1.jpg",
    "created_at": "2024-01-08T10:00:00"
  }
}
```

#### Download DICOM File
```http
GET http://localhost:5000/api/dicom/images/<image_id>/file
Cookie: session=<your-session-cookie>
```

**Example:**
```http
GET http://localhost:5000/api/dicom/images/1/file
Cookie: session=<your-session-cookie>
```

**Response:** Binary DICOM file (downloads automatically)

**In Postman:**
- Click "Send and Download" to save the file
- File will be saved as `.dcm` file

#### Get Thumbnail
```http
GET http://localhost:5000/api/dicom/images/<image_id>/thumbnail
Cookie: session=<your-session-cookie>
```

**Example:**
```http
GET http://localhost:5000/api/dicom/images/1/thumbnail
Cookie: session=<your-session-cookie>
```

**Response:** JPEG image (displays in Postman)

---

### 5. Patient Studies

#### Get All Studies for a Patient
```http
GET http://localhost:5000/api/dicom/patients/<patient_id>/studies
Cookie: session=<your-session-cookie>
```

**Example:**
```http
GET http://localhost:5000/api/dicom/patients/P001/studies
Cookie: session=<your-session-cookie>
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "patient_id": "P001",
    "patient_name": "John Doe",
    "studies": [
      {
        "study_instance_uid": "1.2.3.4.5",
        "study_date": "2024-01-08",
        "modality": "US",
        "image_count": 5
      }
    ]
  }
}
```

---

### 6. MWL Operations

#### Send MWL for Appointment
```http
POST http://localhost:5000/api/dicom/appointments/<appointment_id>/send-mwl
Cookie: session=<your-session-cookie>
```

**Example:**
```http
POST http://localhost:5000/api/dicom/appointments/1/send-mwl
Cookie: session=<your-session-cookie>
```

**Expected Response:**
```json
{
  "success": true,
  "message": "MWL sent successfully",
  "data": {
    "appointment_id": 1,
    "patient_id": "P001",
    "date": "2024-01-15",
    "time": "10:00",
    "status": "Waiting",
    "mwl_server_status": "running"
  }
}
```

**Note:** This makes the appointment available in the MWL worklist. A real DICOM device would query this worklist.

---

### 7. Measurements

#### List Measurements
```http
GET http://localhost:5000/api/dicom/measurements?page=1&limit=20
Cookie: session=<your-session-cookie>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `patient_id`: Filter by patient ID (optional)
- `study_instance_uid`: Filter by study UID (optional)

**Example:**
```http
GET http://localhost:5000/api/dicom/measurements?patient_id=P001
Cookie: session=<your-session-cookie>
```

---

## 🧪 Testing Without Real DICOM Data

### Option 1: Test with Empty Database

**What you'll see:**
- Empty lists (no studies/images)
- Server status shows servers running
- All endpoints return valid responses (just empty data)

**This tests:**
- ✅ API endpoints work correctly
- ✅ Authentication works
- ✅ Pagination works
- ✅ Error handling works

### Option 2: Create Test Data Manually

**You can manually insert test data into the database:**

```sql
-- Connect to your database
psql $DATABASE_URL

-- Insert test patient
INSERT INTO patients (id, first_name, last_name, date_of_birth, gender, phone)
VALUES ('P001', 'John', 'Doe', '1990-01-01', 'M', '1234567890');

-- Insert test DICOM image (simplified)
INSERT INTO dicom_images (
    sop_instance_uid, study_instance_uid, series_instance_uid,
    patient_id, patient_name, study_date, modality, file_path
) VALUES (
    '1.2.840.113619.2.55.3.1234567890.1234567890123.1',
    '1.2.840.113619.2.55.3.1234567890.1234567890123',
    '1.2.840.113619.2.55.3.1234567890.1234567890123.1',
    'P001',
    'John^Doe',
    '2024-01-08',
    'US',
    'dicom_files/test.dcm'
);
```

**Then test endpoints with this data.**

### Option 3: Use DICOM Testing Tools (Advanced)

**If you want to simulate a DICOM device:**

1. **DCMTK tools** (command-line DICOM tools)
   ```bash
   # Install DCMTK
   sudo apt install dcmtk  # Linux
   brew install dcmtk      # macOS
   
   # Send test DICOM file
   storescu -aec STORESCP localhost 11113 test.dcm
   ```

2. **DICOM Testing Software:**
   - **DICOMscope** (GUI tool)
   - **DICOM Viewer** (various tools)
   - **pynetdicom** (Python library - you already have it!)

---

## 📝 Postman Collection Setup

### Create Collection Structure

1. **Create Collection:** "Clinic DICOM API"

2. **Create Folders:**
   - `01 - Authentication`
   - `02 - Server Management`
   - `03 - Studies`
   - `04 - Images`
   - `05 - Patients`
   - `06 - MWL Operations`
   - `07 - Measurements`

3. **Set Collection Variables:**
   - `base_url`: `http://localhost:5000`
   - `session_cookie`: (set after login)

4. **Add Pre-request Script** (for auto-cookie):
   ```javascript
   // Auto-add session cookie
   pm.request.headers.add({
       key: 'Cookie',
       value: pm.collectionVariables.get('session_cookie')
   });
   ```

---

## ✅ Testing Checklist

### Basic Functionality
- [ ] Login and get session cookie
- [ ] Get server status
- [ ] Start DICOM servers
- [ ] List studies (empty or with data)
- [ ] List images (empty or with data)
- [ ] Get image details
- [ ] Download DICOM file
- [ ] Get thumbnail

### Advanced Testing
- [ ] Filter studies by patient_id
- [ ] Filter images by modality
- [ ] Pagination (test page 1, 2, etc.)
- [ ] Get patient studies
- [ ] Send MWL for appointment
- [ ] List measurements

### Error Handling
- [ ] Test without authentication (should fail)
- [ ] Test invalid image_id (should return 404)
- [ ] Test invalid study_uid (should return 404)
- [ ] Test invalid pagination (should handle gracefully)

---

## 🎯 Quick Test Flow

### 1. Setup
```bash
# Start backend
python run.py
```

### 2. Login
```http
POST http://localhost:5000/api/auth/login
Body: {"username": "admin", "password": "admin123"}
```

### 3. Test Endpoints
```http
# Check status
GET http://localhost:5000/api/dicom/server/status

# List studies
GET http://localhost:5000/api/dicom/studies

# List images
GET http://localhost:5000/api/dicom/images
```

---

## 📊 Expected Results

### With Empty Database:
- ✅ All endpoints return `200 OK`
- ✅ Lists return empty arrays: `{"studies": [], "pagination": {...}}`
- ✅ Server status shows servers running
- ✅ No errors (just empty data)

### With Test Data:
- ✅ Lists show your test data
- ✅ Can download files
- ✅ Can view thumbnails
- ✅ Filters work correctly

---

## 🔍 Troubleshooting

### Issue: "Authentication required"
**Solution:** Make sure you're sending the session cookie from login.

### Issue: "Empty lists"
**Solution:** This is normal if no DICOM data exists. Create test data or wait for real device to send images.

### Issue: "Servers not running"
**Solution:** 
```http
POST http://localhost:5000/api/dicom/server/start
```

### Issue: "Cannot download file"
**Solution:** Check if file exists in `dicom_files/` directory. If database has entry but file missing, you'll get 404.

---

## 📚 Summary

**What you CAN test:**
- ✅ All HTTP endpoints
- ✅ Authentication
- ✅ Server management
- ✅ Data retrieval (studies, images)
- ✅ File downloads
- ✅ Thumbnails
- ✅ Filtering and pagination

**What you CANNOT test without device:**
- ❌ MWL queries from device (but API endpoint works)
- ❌ C-STORE image reception (but you can test with DCMTK tools)

**Bottom line:** You can test **95% of DICOM API functionality** without a physical device!

---

**Last Updated:** 2024-01-08

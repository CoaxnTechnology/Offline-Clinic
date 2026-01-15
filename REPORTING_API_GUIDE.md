# Reporting API - Complete Guide

## ✅ Implementation Complete

The Reporting API is now fully implemented with all endpoints, PDF generation, and database support.

---

## 📋 API Endpoints

### 1. Generate Report
**POST** `/api/reports/generate`

Generate a PDF report for a DICOM study.

**Request Body:**
```json
{
  "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123",
  "patient_id": "P001",
  "report_number": "RPT-20240108-ABC123",
  "notes": "Routine ultrasound examination",
  "async": false
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Report generated successfully",
  "data": {
    "id": 1,
    "report_number": "RPT-20240108-ABC123",
    "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123",
    "patient_id": "P001",
    "patient_name": "John Doe",
    "status": "completed",
    "file_path": "/path/to/report.pdf",
    "file_size": 123456,
    "image_count": 5
  }
}
```

**Access:** Doctor, Technician

---

### 2. List Reports
**GET** `/api/reports`

List all reports with pagination and filters.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)
- `patient_id`: Filter by patient ID
- `study_instance_uid`: Filter by study UID
- `status`: Filter by status (completed, generating, failed)

**Example:**
```
GET /api/reports?patient_id=P001&page=1&limit=20
```

**Response:**
```json
{
  "success": true,
  "data": {
    "reports": [
      {
        "id": 1,
        "report_number": "RPT-20240108-ABC123",
        "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123",
        "patient_id": "P001",
        "patient_name": "John Doe",
        "status": "completed",
        "report_date": "2024-01-08",
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

**Access:** All authenticated users

---

### 3. Get Report Details
**GET** `/api/reports/<report_id>`

Get detailed information about a specific report.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "report_number": "RPT-20240108-ABC123",
    "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123",
    "patient_id": "P001",
    "patient_name": "John Doe",
    "report_type": "DICOM Study Report",
    "report_date": "2024-01-08",
    "status": "completed",
    "file_path": "/path/to/report.pdf",
    "file_size": 123456,
    "image_count": 5,
    "created_at": "2024-01-08T10:00:00",
    "updated_at": "2024-01-08T10:00:00"
  }
}
```

**Access:** All authenticated users

---

### 4. Get Report by Number
**GET** `/api/reports/number/<report_number>`

Get report details by report number.

**Example:**
```
GET /api/reports/number/RPT-20240108-ABC123
```

**Access:** All authenticated users

---

### 5. Download Report PDF
**GET** `/api/reports/<report_id>/download`

Download the PDF file for a report.

**Response:** PDF file (binary)

**Access:** All authenticated users

---

### 6. Get Report Status
**GET** `/api/reports/<report_id>/status`

Check the generation status of a report (useful for async generation).

**Response:**
```json
{
  "success": true,
  "data": {
    "report_id": 1,
    "report_number": "RPT-20240108-ABC123",
    "status": "completed",
    "task_status": "SUCCESS",
    "created_at": "2024-01-08T10:00:00"
  }
}
```

**Status values:**
- `generating`: Report is being generated
- `completed`: Report is ready
- `failed`: Report generation failed

**Access:** All authenticated users

---

### 7. Delete Report
**DELETE** `/api/reports/<report_id>`

Delete a report and its PDF file.

**Response:**
```json
{
  "success": true,
  "message": "Report deleted successfully"
}
```

**Access:** Doctor, Receptionist

---

## 🧪 Testing with Postman

### Step 1: Login
```http
POST http://localhost:5000/api/auth/login
Content-Type: application/json

{
  "username": "doctor1",
  "password": "doctor123"
}
```

Save the session cookie.

### Step 2: Generate Report
```http
POST http://localhost:5000/api/reports/generate
Cookie: session=<your-session-cookie>
Content-Type: application/json

{
  "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123",
  "patient_id": "P001",
  "notes": "Routine examination"
}
```

### Step 3: List Reports
```http
GET http://localhost:5000/api/reports?page=1&limit=20
Cookie: session=<your-session-cookie>
```

### Step 4: Download Report
```http
GET http://localhost:5000/api/reports/1/download
Cookie: session=<your-session-cookie>
```

Click "Send and Download" in Postman to save the PDF.

---

## 📊 Database Model

### Report Table

**Fields:**
- `id`: Primary key
- `report_number`: Unique report identifier (e.g., RPT-20240108-ABC123)
- `study_instance_uid`: Associated DICOM study
- `patient_id`: Patient ID (foreign key)
- `patient_name`: Denormalized patient name
- `report_type`: Type of report (default: "DICOM Study Report")
- `report_date`: Date of report
- `file_path`: Path to PDF file
- `file_size`: File size in bytes
- `status`: Status (completed, generating, failed)
- `generation_task_id`: Celery task ID (if async)
- `image_count`: Number of images in study
- `generated_by`: Admin ID who generated report
- `notes`: Additional notes
- `created_at`, `updated_at`: Timestamps

---

## 🔧 Features

### 1. Synchronous Generation
Generate PDF immediately and return result:
```json
{
  "async": false
}
```

### 2. Asynchronous Generation
Queue report generation via Celery:
```json
{
  "async": true
}
```

Returns task ID for status checking.

### 3. PDF Generation
- Uses WeasyPrint for professional PDFs
- Includes patient information
- Includes study details
- Includes image thumbnails (if available)
- Professional formatting with CSS

### 4. Error Handling
- Validates study exists
- Handles missing images
- Handles PDF generation failures
- Updates report status accordingly

---

## 📝 Migration

**Run migration:**
```bash
flask db upgrade
```

**Migration file:** `migrations/versions/0f452f437c97_add_report_model_for_pdf_reports.py`

---

## 🎯 Usage Examples

### Generate Report for Study
```python
# Via API
POST /api/reports/generate
{
  "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123",
  "patient_id": "P001"
}
```

### List Patient Reports
```python
# Via API
GET /api/reports?patient_id=P001
```

### Download Report
```python
# Via API
GET /api/reports/1/download
# Returns PDF file
```

---

## ✅ Summary

**Implemented:**
- ✅ Report model with database
- ✅ PDF generation with WeasyPrint
- ✅ Service layer with business logic
- ✅ All API endpoints (7 endpoints)
- ✅ Async generation support (Celery)
- ✅ Error handling and validation
- ✅ Blueprint registered

**Endpoints:**
- ✅ POST `/api/reports/generate` - Generate report
- ✅ GET `/api/reports` - List reports
- ✅ GET `/api/reports/<id>` - Get report details
- ✅ GET `/api/reports/number/<number>` - Get by report number
- ✅ GET `/api/reports/<id>/download` - Download PDF
- ✅ GET `/api/reports/<id>/status` - Get status
- ✅ DELETE `/api/reports/<id>` - Delete report

**Status:** ✅ **Complete and Ready to Use**

---

**Last Updated:** 2024-01-08

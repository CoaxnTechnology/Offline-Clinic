# API Testing Guide

Complete guide for testing all Clinic Backend APIs using Postman or curl.

## Table of Contents

1. [Authentication API](#authentication-api)
2. [Patient API](#patient-api)
3. [Appointment API](#appointment-api)
4. [DICOM API](#dicom-api)
5. [Admin Management API](#admin-management-api)
   - [Creating Roles (Doctor, Technician, Receptionist)](#creating-roles-doctor-technician-receptionist)
6. [Test Users](#test-users)
7. [Common Error Responses](#common-error-responses)

---

## Base URL

```
http://localhost:5000
```

---

## Authentication API

### 1. Login

**Endpoint:** `POST /api/auth/login`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "doctor1",
  "password": "doctor123"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "username": "doctor1",
    "email": "doctor1@clinic.com",
    "role": "doctor",
    "first_name": "John",
    "last_name": "Doctor"
  }
}
```

**Error Response (401):**
```json
{
  "success": false,
    "error": "Invalid username or password"
}
```

**Postman Setup:**
- Method: POST
- URL: `http://localhost:5000/api/auth/login`
- Body → raw → JSON
- After login, cookies are automatically saved

---

### 2. Get Current User

**Endpoint:** `GET /api/auth/me`

**Headers:**
```
(No headers needed - uses cookies automatically)
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "username": "doctor1",
    "email": "doctor1@clinic.com",
    "role": "doctor",
    "first_name": "John",
    "last_name": "Doctor",
    "phone": null,
    "is_active": true,
    "last_login": "2024-01-07T10:30:00",
    "login_count": 1
  }
}
```

**Postman Setup:**
- Method: GET
- URL: `http://localhost:5000/api/auth/me`
- Cookies are sent automatically

---

### 3. Logout

**Endpoint:** `POST /api/auth/logout`

**Success Response (200):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

**Postman Setup:**
- Method: POST
- URL: `http://localhost:5000/api/auth/logout`

---

## Patient API

### 1. List Patients

**Endpoint:** `GET /api/patients`

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)
- `search` (optional): Search query (searches name, phone, email, ID)

**Example Request:**
```
GET /api/patients?page=1&limit=10&search=john
```

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "P001",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "1234567890",
      "email": "john@example.com",
      "gender": "Male",
      "birth_date": "1990-01-15",
      "created_at": "2024-01-07T10:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 25,
    "pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

**Postman Setup:**
- Method: GET
- URL: `http://localhost:5000/api/patients?page=1&limit=10&search=john`
- Params tab: Add `page`, `limit`, `search`

---

### 2. Get Single Patient

**Endpoint:** `GET /api/patients/<patient_id>`

**Example Request:**
```
GET /api/patients/P001
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": "P001",
    "title": null,
    "first_name": "John",
    "last_name": "Doe",
    "gender": "Male",
    "birth_date": "1990-01-15",
    "phone": "1234567890",
    "email": "john@example.com",
    "identity_number": null,
    "height": 175.0,
    "weight": 70.5,
    "blood_group": "O+",
    "notes": null,
    "primary_doctor": null,
    "new_patient": true,
    "demographics": null,
    "created_at": "2024-01-07T10:00:00",
    "updated_at": "2024-01-07T10:00:00"
  }
}
```

**Error Response (404):**
```json
{
  "success": false,
  "error": "Patient not found"
}
```

---

### 3. Create Patient

**Endpoint:** `POST /api/patients`

**Access:** receptionist, doctor

**Request Body:**
```json
{
  "id": "P001",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "1234567890",
  "email": "john@example.com",
  "gender": "Male",
  "birth_date": "1990-01-15",
  "height": 175.0,
  "weight": 70.5,
  "blood_group": "O+",
  "title": "Mr",
  "identity_number": "ID123456",
  "notes": "Regular patient",
  "primary_doctor": "Dr. Smith",
  "new_patient": true
}
```

**Required Fields:**
- `id`
- `first_name`
- `last_name`
- `phone`

**Success Response (201):**
```json
{
  "success": true,
  "data": {
    "id": "P001",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "1234567890",
    "email": "john@example.com",
    "gender": "Male",
    "birth_date": "1990-01-15",
    "created_at": "2024-01-07T10:00:00"
  },
  "message": "Patient created successfully"
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Patient with ID P001 already exists"
}
```

---

### 4. Update Patient

**Endpoint:** `PUT /api/patients/<patient_id>`

**Access:** receptionist, doctor

**Request Body:**
```json
{
  "weight": 72.0,
  "email": "newemail@example.com",
  "notes": "Updated notes"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": "P001",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "1234567890",
    "email": "newemail@example.com",
    "gender": "Male",
    "birth_date": "1990-01-15",
    "updated_at": "2024-01-07T11:00:00"
  },
  "message": "Patient updated successfully"
}
```

---

### 5. Delete Patient

**Endpoint:** `DELETE /api/patients/<patient_id>`

**Access:** receptionist, doctor

**Example Request:**
```
DELETE /api/patients/P001
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Patient P001 deleted successfully"
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Cannot delete patient. Patient has 3 appointment(s)."
}
```

---

### 6. Search Patients

**Endpoint:** `GET /api/patients/search`

**Query Parameters:**
- `q` (required): Search query

**Example Request:**
```
GET /api/patients/search?q=john
```

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": "P001",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "1234567890",
      "email": "john@example.com",
      "gender": "Male",
      "birth_date": "1990-01-15"
    }
  ],
  "count": 1
}
```

---

## Appointment API

### 1. List Appointments

**Endpoint:** `GET /api/appointments`

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)
- `date` (optional): Filter by date (format: YYYY-MM-DD)
- `patient_id` (optional): Filter by patient ID
- `doctor` (optional): Filter by doctor name
- `status` (optional): Filter by status

**Example Request:**
```
GET /api/appointments?date=2024-01-20&status=Waiting&page=1&limit=10
```

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "patient_id": "P001",
      "patient_name": "John Doe",
      "doctor": "Dr. Smith",
      "department": "Cardiology",
      "date": "2024-01-20",
      "time": "10:30",
      "status": "Waiting",
      "created_at": "2024-01-07T10:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 25,
    "pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### 2. Get Single Appointment

**Endpoint:** `GET /api/appointments/<id>`

**Example Request:**
```
GET /api/appointments/1
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "patient_id": "P001",
    "patient": {
      "id": "P001",
      "name": "John Doe",
      "phone": "1234567890"
    },
    "doctor": "Dr. Smith",
    "department": "Cardiology",
    "date": "2024-01-20",
    "time": "10:30",
    "status": "Waiting",
    "created_at": "2024-01-07T10:00:00",
    "updated_at": "2024-01-07T10:00:00"
  }
}
```

---

### 3. Create Appointment

**Endpoint:** `POST /api/appointments`

**Access:** receptionist, doctor

**Request Body:**
```json
{
  "patient_id": "P001",
  "doctor": "Dr. Smith",
  "department": "Cardiology",
  "date": "2024-01-20",
  "time": "10:30",
  "status": "Waiting"
}
```

**Required Fields:**
- `patient_id`
- `doctor`
- `date` (format: YYYY-MM-DD)
- `time` (format: HH:MM)

**Success Response (201):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "patient_id": "P001",
    "patient_name": "John Doe",
    "doctor": "Dr. Smith",
    "department": "Cardiology",
    "date": "2024-01-20",
    "time": "10:30",
    "status": "Waiting",
    "created_at": "2024-01-07T10:00:00"
  },
  "message": "Appointment created successfully"
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Appointment already exists for this patient, doctor, date, and time"
}
```

---

### 4. Update Appointment

**Endpoint:** `PUT /api/appointments/<id>`

**Access:** receptionist, doctor, technician

**Request Body:**
```json
{
  "time": "11:00",
  "department": "Radiology",
  "doctor": "Dr. Johnson"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "patient_id": "P001",
    "patient_name": "John Doe",
    "doctor": "Dr. Johnson",
    "department": "Radiology",
    "date": "2024-01-20",
    "time": "11:00",
    "status": "Waiting",
    "updated_at": "2024-01-07T11:00:00"
  },
  "message": "Appointment updated successfully"
}
```

---

### 5. Update Appointment Status

**Endpoint:** `PUT /api/appointments/<id>/status`

**Access:** doctor, technician

**Request Body:**
```json
{
  "status": "In-Room"
}
```

**Valid Status Values:**
- `Waiting`
- `In-Room`
- `In-Scan`
- `With Doctor`
- `With Technician`
- `Review`
- `Completed`

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "patient_id": "P001",
    "patient_name": "John Doe",
    "status": "In-Room",
    "updated_at": "2024-01-07T11:00:00"
  },
  "message": "Appointment status updated to In-Room"
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Invalid status. Valid values: Waiting, In-Room, In-Scan, With Doctor, With Technician, Review, Completed"
}
```

---

### 6. Delete Appointment

**Endpoint:** `DELETE /api/appointments/<id>`

**Access:** receptionist, doctor

**Example Request:**
```
DELETE /api/appointments/1
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Appointment 1 deleted successfully",
  "data": {
    "id": 1,
    "patient_id": "P001",
    "date": "2024-01-20",
    "time": "10:30"
  }
}
```

---

### 7. Bulk Schedule Appointments

**Endpoint:** `POST /api/appointments/schedule`

**Access:** receptionist only

**Request Body:**
```json
[
  {
    "patient_id": "P001",
    "doctor": "Dr. Smith",
    "department": "Cardiology",
    "date": "2024-01-20",
    "time": "10:30",
    "status": "Waiting"
  },
  {
    "patient_id": "P002",
    "doctor": "Dr. Johnson",
    "department": "Radiology",
    "date": "2024-01-20",
    "time": "11:00",
    "status": "Waiting"
  }
]
```

**Success Response (201):**
```json
{
  "success": true,
  "message": "Created 2 appointment(s)",
  "data": {
    "created": [
      {
        "index": 0,
        "patient_id": "P001",
        "doctor": "Dr. Smith",
        "date": "2024-01-20",
        "time": "10:30"
      },
      {
        "index": 1,
        "patient_id": "P002",
        "doctor": "Dr. Johnson",
        "date": "2024-01-20",
        "time": "11:00"
      }
    ],
    "errors": []
  }
}
```

**Partial Success Response (201):**
```json
{
  "success": true,
  "message": "Created 1 appointment(s)",
  "data": {
    "created": [
      {
        "index": 0,
        "patient_id": "P001",
        "doctor": "Dr. Smith",
        "date": "2024-01-20",
        "time": "10:30"
      }
    ],
    "errors": [
      {
        "index": 1,
        "error": "Patient P002 not found"
      }
    ]
  }
}
```

**Note:** Maximum 50 appointments can be scheduled at once.

---

## DICOM API

### Prerequisites

Before testing DICOM API, ensure:
1. DICOM servers are running (see [Start DICOM Servers](#start-dicom-servers))
2. You have created at least one patient and appointment
3. You are logged in as doctor or technician for server management

---

### 1. Start DICOM Servers

**Endpoint:** `POST /api/dicom/server/start`

**Access:** doctor, technician

**Request:**
```
POST /api/dicom/server/start
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "DICOM servers started",
  "data": {
    "mwl_server_running": true,
    "storage_server_running": true,
    "mwl_port": 11112,
    "storage_port": 11113,
    "ae_title": "STORESCP"
  }
}
```

**Postman Setup:**
- Method: POST
- URL: `http://localhost:5000/api/dicom/server/start`
- Headers: (uses cookies automatically)

**Note:** Servers can also be started by running `python dicom_listener.py` in terminal.

---

### 2. Get DICOM Server Status

**Endpoint:** `GET /api/dicom/server/status`

**Access:** doctor, technician

**Request:**
```
GET /api/dicom/server/status
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "mwl_server_running": true,
    "storage_server_running": true,
    "mwl_port": 11112,
    "storage_port": 11113,
    "ae_title": "STORESCP"
  }
}
```

**Postman Setup:**
- Method: GET
- URL: `http://localhost:5000/api/dicom/server/status`

---

### 3. Stop DICOM Servers

**Endpoint:** `POST /api/dicom/server/stop`

**Access:** doctor, technician

**Request:**
```
POST /api/dicom/server/stop
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "DICOM servers stopped"
}
```

---

### 4. Send MWL for Appointment

**Endpoint:** `POST /api/dicom/appointments/<appointment_id>/send-mwl`

**Access:** receptionist, doctor

**Description:** Makes an appointment available in the DICOM Modality Worklist. When a DICOM device queries the worklist, this appointment will appear.

**Request:**
```
POST /api/dicom/appointments/1/send-mwl
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Appointment 1 is now available in MWL",
  "data": {
    "appointment_id": 1,
    "patient_id": "P001",
    "patient_name": "John Doe",
    "date": "2024-01-20",
    "time": "10:30",
    "department": "Cardiology",
    "status": "Waiting"
  }
}
```

**Postman Setup:**
- Method: POST
- URL: `http://localhost:5000/api/dicom/appointments/1/send-mwl`
- Replace `1` with actual appointment ID

**Workflow:**
1. Create appointment (if not exists)
2. Send MWL for that appointment
3. On DICOM device, query worklist (search with today's date)
4. Appointment should appear in device worklist
5. After scanning, device sends images back to storage server

---

### 5. List DICOM Studies

**Endpoint:** `GET /api/dicom/studies`

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)
- `patient_id` (optional): Filter by patient ID
- `study_date` (optional): Filter by study date (YYYY-MM-DD)
- `accession_number` (optional): Filter by accession number

**Example Request:**
```
GET /api/dicom/studies?patient_id=P001&page=1&limit=10
```

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123456",
      "patient_id": "P001",
      "patient_name": "John Doe",
      "study_date": "2024-01-20",
      "study_time": "103000",
      "study_description": "Ultrasound",
      "accession_number": "ACC000001",
      "referring_physician": "Dr. Smith",
      "institution_name": "Clinic",
      "series_count": 2,
      "created_at": "2024-01-20T10:30:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

**Postman Setup:**
- Method: GET
- URL: `http://localhost:5000/api/dicom/studies`
- Params tab: Add `patient_id`, `study_date`, `page`, `limit`

---

### 6. Get DICOM Study Details

**Endpoint:** `GET /api/dicom/studies/<study_id>`

**Example Request:**
```
GET /api/dicom/studies/1
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123456",
    "patient": {
      "id": "P001",
      "name": "John Doe",
      "gender": "Male",
      "birth_date": "1990-01-15"
    },
    "study_date": "2024-01-20",
    "study_time": "103000",
    "study_description": "Ultrasound",
    "accession_number": "ACC000001",
    "referring_physician": "Dr. Smith",
    "institution_name": "Clinic",
    "series": [
      {
        "id": 1,
        "series_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123457",
        "modality": "US",
        "series_number": 1,
        "series_description": "Abdomen",
        "body_part_examined": "ABDOMEN",
        "manufacturer": "SAMSUNG",
        "image_count": 5
      }
    ],
    "created_at": "2024-01-20T10:30:00"
  }
}
```

**Postman Setup:**
- Method: GET
- URL: `http://localhost:5000/api/dicom/studies/1`
- Replace `1` with actual study ID

---

### 7. List DICOM Images

**Endpoint:** `GET /api/dicom/images`

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)
- `patient_id` (optional): Filter by patient ID
- `study_instance_uid` (optional): Filter by study UID
- `series_instance_uid` (optional): Filter by series UID
- `modality` (optional): Filter by modality (US, CT, MR, etc.)

**Example Request:**
```
GET /api/dicom/images?patient_id=P001&modality=US&page=1&limit=20
```

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "sop_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123458",
      "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123456",
      "series_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123457",
      "patient_id": "P001",
      "patient_name": "John Doe",
      "patient_birth_date": "1990-01-15",
      "patient_sex": "M",
      "accession_number": "ACC000001",
      "study_date": "2024-01-20",
      "study_time": "103000",
      "study_description": "Ultrasound",
      "modality": "US",
      "body_part_examined": "ABDOMEN",
      "manufacturer": "SAMSUNG",
      "file_path": "dicom_files/20240120/1.2.840.113619.2.55.3.1234567890.1234567890123458.dcm",
      "thumbnail_path": "thumbnails/1.2.840.113619.2.55.3.1234567890.1234567890123458.jpg",
      "created_at": "2024-01-20T10:30:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

**Postman Setup:**
- Method: GET
- URL: `http://localhost:5000/api/dicom/images`
- Params tab: Add filters as needed

---

### 8. Get DICOM Image Details

**Endpoint:** `GET /api/dicom/images/<image_id>`

**Example Request:**
```
GET /api/dicom/images/1
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "sop_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123458",
    "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123456",
    "series_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123457",
    "patient_id": "P001",
    "patient_name": "John Doe",
    "modality": "US",
    "file_path": "dicom_files/20240120/1.2.840.113619.2.55.3.1234567890.1234567890123458.dcm",
    "thumbnail_path": "thumbnails/1.2.840.113619.2.55.3.1234567890.1234567890123458.jpg",
    "measurements": [
      {
        "id": 1,
        "dicom_image_id": 1,
        "patient_id": "P001",
        "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123456",
        "measurement_type": "Study",
        "measurement_value": "Received",
        "measurement_data": "{\"status\": \"received\", \"modality\": \"US\"}",
        "created_at": "2024-01-20T10:30:00"
      }
    ],
    "created_at": "2024-01-20T10:30:00"
  }
}
```

---

### 9. Download DICOM File

**Endpoint:** `GET /api/dicom/images/<image_id>/file`

**Description:** Downloads the actual DICOM (.dcm) file

**Example Request:**
```
GET /api/dicom/images/1/file
```

**Success Response (200):**
- Content-Type: `application/dicom`
- File download with name: `{sop_instance_uid}.dcm`

**Postman Setup:**
- Method: GET
- URL: `http://localhost:5000/api/dicom/images/1/file`
- Click "Send and Download" to save file

**Note:** In Postman, the file will be downloaded automatically. In browser, it will prompt for download.

---

### 10. Get Image Thumbnail

**Endpoint:** `GET /api/dicom/images/<image_id>/thumbnail`

**Description:** Returns thumbnail image (JPEG)

**Example Request:**
```
GET /api/dicom/images/1/thumbnail
```

**Success Response (200):**
- Content-Type: `image/jpeg`
- JPEG image data

**Postman Setup:**
- Method: GET
- URL: `http://localhost:5000/api/dicom/images/1/thumbnail`
- In Postman, you can see the image in the response (if "Send and Download" is not used)

**Note:** Thumbnails are automatically generated when DICOM images are received.

---

### 11. List Measurements

**Endpoint:** `GET /api/dicom/measurements`

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)
- `patient_id` (optional): Filter by patient ID
- `study_instance_uid` (optional): Filter by study UID
- `measurement_type` (optional): Filter by measurement type

**Example Request:**
```
GET /api/dicom/measurements?patient_id=P001
```

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "dicom_image_id": 1,
      "patient_id": "P001",
      "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123456",
      "measurement_type": "Study",
      "measurement_value": "Received",
      "measurement_data": "{\"status\": \"received\", \"modality\": \"US\"}",
      "created_at": "2024-01-20T10:30:00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### 12. Get Patient Studies

**Endpoint:** `GET /api/dicom/patients/<patient_id>/studies`

**Description:** Get all DICOM studies for a specific patient

**Example Request:**
```
GET /api/dicom/patients/P001/studies
```

**Success Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "study_instance_uid": "1.2.840.113619.2.55.3.1234567890.1234567890123456",
      "study_date": "2024-01-20",
      "study_time": "103000",
      "study_description": "Ultrasound",
      "accession_number": "ACC000001",
      "series_count": 2,
      "created_at": "2024-01-20T10:30:00"
    }
  ],
  "patient": {
    "id": "P001",
    "name": "John Doe"
  }
}
```

---

## DICOM Testing Workflow

### Complete DICOM Workflow Test

**Step 1: Start Flask Server**
```bash
cd /home/raza/Projects/Clinic/backend
uv run flask run
```

**Step 2: Start DICOM Servers**
- POST `/api/dicom/server/start`
- Or run: `python dicom_listener.py` in separate terminal

**Step 3: Login**
- POST `/api/auth/login` with doctor credentials

**Step 4: Create Patient** (if not exists)
- POST `/api/patients` with patient data

**Step 5: Create Appointment**
- POST `/api/appointments` with appointment data

**Step 6: Send MWL**
- POST `/api/dicom/appointments/<appointment_id>/send-mwl`
- This makes appointment available in DICOM worklist

**Step 7: Query Worklist on DICOM Device**
- On ultrasound machine, search worklist with today's date
- Appointment should appear
- Select and scan patient

**Step 8: Device Sends Images**
- After scanning, device automatically sends images to storage server
- Images are automatically stored and processed

**Step 9: Verify Images Received**
- GET `/api/dicom/images` - Should show received images
- GET `/api/dicom/studies` - Should show study created
- GET `/api/dicom/images/<id>/thumbnail` - View thumbnail

**Step 10: Download DICOM File**
- GET `/api/dicom/images/<id>/file` - Download original DICOM file

---

## Admin Management API

### How to Create Roles (Doctor, Technician, Receptionist) via Postman

**Important:** Roles are created by creating admin users with specific roles. Only **super admin** can create new admin users.

**Quick Summary:**
- Login as super admin (`admin` / `admin123`)
- Use `POST /api/admin` endpoint
- Specify `role` field: `doctor`, `technician`, or `receptionist`
- New user is created with that role

#### Step 1: Login as Super Admin

**Endpoint:** `POST /api/auth/login`

**Request:**
```
POST http://localhost:5000/api/auth/login
Body: {
  "username": "admin",
  "password": "admin123"
}
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "admin",
    "role": "doctor",
    "is_super_admin": true
  }
}
```

#### Step 2: Create Doctor Role

**Endpoint:** `POST /api/admin`

**Access:** Super admin only

**Postman Setup:**
1. **Method:** `POST`
2. **URL:** `http://localhost:5000/api/admin`
3. **Headers:**
   - `Content-Type: application/json`
   - Cookies are sent automatically (from login)
4. **Body:** Select `raw` → `JSON`

**Request Body:**
```json
{
  "username": "doctor2",
  "email": "doctor2@clinic.com",
  "password": "doctor123",
  "first_name": "Jane",
  "last_name": "Smith",
  "role": "doctor",
  "phone": "9876543210"
}
```

**Success Response (201):**
```json
{
  "success": true,
  "data": {
    "id": 5,
    "username": "doctor2",
    "email": "doctor2@clinic.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "phone": "9876543210",
    "role": "doctor",
    "is_active": true,
    "is_super_admin": false,
    "created_at": "2024-01-08T10:00:00"
  },
  "message": "Admin user \"doctor2\" created successfully"
}
```

**✅ Doctor role created!** User can now login with `doctor2` / `doctor123` and has doctor permissions.

#### Step 3: Create Technician Role

**Postman Setup:**
- **Method:** `POST`
- **URL:** `http://localhost:5000/api/admin`
- **Body → raw → JSON:**

**Request Body:**
```json
{
  "username": "technician2",
  "email": "technician2@clinic.com",
  "password": "tech123",
  "first_name": "Bob",
  "last_name": "Johnson",
  "role": "technician",
  "phone": "9876543211"
}
```

**Success Response (201):**
```json
{
  "success": true,
  "data": {
    "id": 6,
    "username": "technician2",
    "email": "technician2@clinic.com",
    "first_name": "Bob",
    "last_name": "Johnson",
    "role": "technician",
    "is_active": true,
    "created_at": "2024-01-08T10:00:00"
  },
  "message": "Admin user \"technician2\" created successfully"
}
```

**✅ Technician role created!** User can now login with `technician2` / `tech123` and has technician permissions.

#### Step 4: Create Receptionist Role

**Postman Setup:**
- **Method:** `POST`
- **URL:** `http://localhost:5000/api/admin`
- **Body → raw → JSON:**

**Request Body:**
```json
{
  "username": "receptionist2",
  "email": "receptionist2@clinic.com",
  "password": "recep123",
  "first_name": "Alice",
  "last_name": "Williams",
  "role": "receptionist",
  "phone": "9876543212"
}
```

**Success Response (201):**
```json
{
  "success": true,
  "data": {
    "id": 7,
    "username": "receptionist2",
    "email": "receptionist2@clinic.com",
    "first_name": "Alice",
    "last_name": "Williams",
    "role": "receptionist",
    "is_active": true,
    "created_at": "2024-01-08T10:00:00"
  },
  "message": "Admin user \"receptionist2\" created successfully"
}
```

**✅ Receptionist role created!** User can now login with `receptionist2` / `recep123` and has receptionist permissions.

### Postman Collection Setup for Role Creation

**Create a folder:** `Admin Management` in your Postman collection

**Add requests:**

1. **Login as Super Admin**
   - Method: `POST`
   - URL: `{{base_url}}/api/auth/login`
   - Body: `{"username": "admin", "password": "admin123"}`

2. **Create Doctor**
   - Method: `POST`
   - URL: `{{base_url}}/api/admin`
   - Body: (see Step 2 above)

3. **Create Technician**
   - Method: `POST`
   - URL: `{{base_url}}/api/admin`
   - Body: (see Step 3 above)

4. **Create Receptionist**
   - Method: `POST`
   - URL: `{{base_url}}/api/admin`
   - Body: (see Step 4 above)

5. **List All Admins**
   - Method: `GET`
   - URL: `{{base_url}}/api/admin?role=doctor`

### Valid Roles

When creating admin users, use one of these roles in the `role` field:
- `doctor` - Full access to patients, appointments, can update status
- `technician` - Can update appointments and status, view patients
- `receptionist` - Can manage patients, create/update appointments, bulk schedule

### Required Fields

- `username` - Unique username (string)
- `email` - Unique email address (string)
- `password` - Password, minimum 6 characters (will be hashed)
- `first_name` - First name (string)
- `last_name` - Last name (string)
- `role` - One of: `doctor`, `technician`, `receptionist` (string)

### Optional Fields

- `phone` - Phone number (string)

### Complete Example: Create All Three Roles

**In Postman, create 3 requests:**

**Request 1: Create Doctor**
```json
POST {{base_url}}/api/admin
{
  "username": "doctor_new",
  "email": "doctor_new@clinic.com",
  "password": "doctor123",
  "first_name": "Dr. New",
  "last_name": "Doctor",
  "role": "doctor"
}
```

**Request 2: Create Technician**
```json
POST {{base_url}}/api/admin
{
  "username": "tech_new",
  "email": "tech_new@clinic.com",
  "password": "tech123",
  "first_name": "Tech",
  "last_name": "New",
  "role": "technician"
}
```

**Request 3: Create Receptionist**
```json
POST {{base_url}}/api/admin
{
  "username": "recep_new",
  "email": "recep_new@clinic.com",
  "password": "recep123",
  "first_name": "Recep",
  "last_name": "New",
  "role": "receptionist"
}
```

**After creating, verify:**
```
GET {{base_url}}/api/admin
```

You should see all created users with their roles.

#### Error Responses

**Permission Denied (403):**
```json
{
  "success": false,
  "error": "Permission denied. Only super admin can create new admins."
}
```

**Duplicate Username (400):**
```json
{
  "success": false,
  "error": "Username already exists"
}
```

**Invalid Role (400):**
```json
{
  "success": false,
  "error": "Invalid role. Valid roles: doctor, technician, receptionist"
}
```

---

## Test Users

### Default Admin Users

| Username | Password | Role | Access |
|----------|----------|------|--------|
| `admin` | `admin123` | doctor | Full access (super admin) |
| `doctor1` | `doctor123` | doctor | Can manage patients, appointments, reports |
| `technician1` | `tech123` | technician | Can view patients, update appointments, update status |
| `receptionist1` | `recep123` | receptionist | Can manage patients, create/update appointments, bulk schedule |

### Creating Additional Users

Use the Admin Management API above to create more users with any role.

### Verify Created Roles

**List all admins by role:**
```
GET {{base_url}}/api/admin?role=doctor
GET {{base_url}}/api/admin?role=technician
GET {{base_url}}/api/admin?role=receptionist
```

**Get specific admin:**
```
GET {{base_url}}/api/admin/5
```

**Test login with new role:**
```
POST {{base_url}}/api/auth/login
Body: {
  "username": "doctor2",
  "password": "doctor123"
}
```

---

## Other Admin Management Endpoints

### List All Admins

**Endpoint:** `GET /api/admin`

**Query Parameters:**
- `role` (optional): Filter by role (doctor, technician, receptionist)
- `is_active` (optional): Filter by active status (true/false)
- `page` (optional): Page number
- `limit` (optional): Items per page

**Example:**
```
GET http://localhost:5000/api/admin?role=doctor&page=1&limit=10
```

### Update Admin

**Endpoint:** `PUT /api/admin/<admin_id>`

**Access:** Super admin (can update all fields) or own profile (limited fields)

**Example:**
```
PUT http://localhost:5000/api/admin/5
Body: {
  "email": "newemail@clinic.com",
  "phone": "1111111111"
}
```

### Change Password

**Endpoint:** `PUT /api/admin/<admin_id>/password`

**Example:**
```
PUT http://localhost:5000/api/admin/5/password
Body: {
  "old_password": "doctor123",
  "new_password": "newpassword123"
}
```

### Deactivate Admin

**Endpoint:** `DELETE /api/admin/<admin_id>`

**Access:** Super admin only

**Example:**
```
DELETE http://localhost:5000/api/admin/5
```

### Activate Admin

**Endpoint:** `PUT /api/admin/<admin_id>/activate`

**Access:** Super admin only

**Example:**
```
PUT http://localhost:5000/api/admin/5/activate
```

### Role Permissions Summary

**Doctor:**
- ✅ View patients
- ✅ Create/update/delete patients
- ✅ Create/update/delete appointments
- ✅ Update appointment status
- ❌ Cannot bulk schedule appointments

**Technician:**
- ✅ View patients
- ✅ Update appointments
- ✅ Update appointment status
- ❌ Cannot create/delete patients
- ❌ Cannot create/delete appointments

**Receptionist:**
- ✅ Create/update/delete patients
- ✅ Create/update/delete appointments
- ✅ Bulk schedule appointments
- ❌ Cannot update appointment status

---

## Common Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "error": "Field 'patient_id' is required"
}
```

### 401 Unauthorized
```json
{
  "success": false,
  "error": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "error": "Permission denied. Required roles: receptionist, doctor"
}
```

### 404 Not Found
```json
{
  "success": false,
  "error": "Patient not found"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "error": "Failed to create patient: Database error"
}
```

---

## Postman Collection Setup

### 1. Create Environment

Create a new environment in Postman:
- Variable: `base_url` = `http://localhost:5000`

### 2. Create Collection

Create a collection named "Clinic API" with folders:
- Authentication
- Patients
- Appointments
- DICOM
  - Server Management
  - Studies
  - Images
  - Measurements

### 3. Use Environment Variables

In requests, use: `{{base_url}}/api/auth/login`

### 4. Cookie Management

- Postman automatically saves cookies after login
- Cookies are sent automatically in subsequent requests
- After logout, cookies are cleared

---

## Testing Workflow

### Step 1: Start Flask Server
```bash
cd /home/raza/Projects/Clinic/backend
export FLASK_APP=run.py
uv run flask run
```

### Step 2: Login
1. POST `/api/auth/login` with receptionist credentials
2. Verify response and check cookies are saved

### Step 3: Create Patient
1. POST `/api/patients` with patient data
2. Verify patient is created

### Step 4: Create Appointment
1. POST `/api/appointments` with appointment data
2. Use patient_id from Step 3
3. Verify appointment is created

### Step 5: List Appointments
1. GET `/api/appointments?date=2024-01-20`
2. Verify appointment appears in list

### Step 6: Update Status
1. PUT `/api/appointments/1/status` with new status
2. Verify status is updated

### Step 7: Test Filters
1. GET `/api/appointments?status=Waiting`
2. GET `/api/appointments?doctor=Dr. Smith`
3. Verify filters work correctly

---

## curl Examples

### Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"doctor1","password":"doctor123"}' \
  -c cookies.txt
```

### Create Patient
```bash
curl -X POST http://localhost:5000/api/patients \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "id": "P001",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "1234567890",
    "email": "john@example.com"
  }'
```

### List Appointments
```bash
curl -X GET "http://localhost:5000/api/appointments?date=2024-01-20&status=Waiting" \
  -b cookies.txt
```

### Update Status
```bash
curl -X PUT http://localhost:5000/api/appointments/1/status \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"status":"In-Room"}'
```

---

## Tips

1. **Always login first** - Most endpoints require authentication
2. **Check cookies** - Verify cookies are saved after login
3. **Use environment variables** - Makes switching between dev/prod easier
4. **Test error cases** - Try invalid data, missing fields, wrong roles
5. **Check status codes** - 200/201 = success, 400 = bad request, 401 = unauthorized, 403 = forbidden, 404 = not found
6. **Date format** - Always use YYYY-MM-DD format
7. **Time format** - Always use HH:MM format (e.g., 10:30)

---

## Troubleshooting

### Issue: "Authentication required"
**Solution:** Login first and ensure cookies are saved

### Issue: "Permission denied"
**Solution:** Check user role. Use receptionist or doctor for patient/appointment management

### Issue: "Patient not found"
**Solution:** Create patient first or use correct patient_id

### Issue: "Invalid date format"
**Solution:** Use YYYY-MM-DD format (e.g., 2024-01-20)

### Issue: "Appointment already exists"
**Solution:** Check for duplicate appointments with same patient, doctor, date, and time

---

## Quick Reference

| Endpoint | Method | Auth | Role Required |
|----------|--------|------|---------------|
| `/api/auth/login` | POST | No | - |
| `/api/auth/logout` | POST | Yes | - |
| `/api/auth/me` | GET | Yes | - |
| `/api/patients` | GET | Yes | - |
| `/api/patients` | POST | Yes | receptionist, doctor |
| `/api/patients/<id>` | GET | Yes | - |
| `/api/patients/<id>` | PUT | Yes | receptionist, doctor |
| `/api/patients/<id>` | DELETE | Yes | receptionist, doctor |
| `/api/patients/search` | GET | Yes | - |
| `/api/appointments` | GET | Yes | - |
| `/api/appointments` | POST | Yes | receptionist, doctor |
| `/api/appointments/<id>` | GET | Yes | - |
| `/api/appointments/<id>` | PUT | Yes | receptionist, doctor, technician |
| `/api/appointments/<id>/status` | PUT | Yes | doctor, technician |
| `/api/appointments/<id>` | DELETE | Yes | receptionist, doctor |
| `/api/appointments/schedule` | POST | Yes | receptionist |
| `/api/dicom/server/status` | GET | Yes | doctor, technician |
| `/api/dicom/server/start` | POST | Yes | doctor, technician |
| `/api/dicom/server/stop` | POST | Yes | doctor, technician |
| `/api/dicom/appointments/<id>/send-mwl` | POST | Yes | receptionist, doctor |
| `/api/dicom/studies` | GET | Yes | - |
| `/api/dicom/studies/<id>` | GET | Yes | - |
| `/api/dicom/images` | GET | Yes | - |
| `/api/dicom/images/<id>` | GET | Yes | - |
| `/api/dicom/images/<id>/file` | GET | Yes | - |
| `/api/dicom/images/<id>/thumbnail` | GET | Yes | - |
| `/api/dicom/measurements` | GET | Yes | - |
| `/api/dicom/patients/<id>/studies` | GET | Yes | - |

---

**Last Updated:** 2024-01-07

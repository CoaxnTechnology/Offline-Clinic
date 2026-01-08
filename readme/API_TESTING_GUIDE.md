# API Testing Guide

Complete guide for testing all Clinic Backend APIs using Postman or curl.

## Table of Contents

1. [Authentication API](#authentication-api)
2. [Patient API](#patient-api)
3. [Appointment API](#appointment-api)
4. [Test Users](#test-users)
5. [Common Error Responses](#common-error-responses)

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

## Test Users

### Default Admin Users

| Username | Password | Role | Access |
|----------|----------|------|--------|
| `admin` | `admin123` | doctor | Full access |
| `doctor1` | `doctor123` | doctor | Can manage patients, appointments, reports |
| `technician1` | `tech123` | technician | Can view patients, update appointments, update status |
| `receptionist1` | `recep123` | receptionist | Can manage patients, create/update appointments, bulk schedule |

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

---

**Last Updated:** 2024-01-07

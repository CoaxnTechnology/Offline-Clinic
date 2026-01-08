# Integration Guide: MWL.py with Backend Database

## Overview

This guide explains how to integrate `mwl.py` (DICOM MWL server) with your existing Flask backend and PostgreSQL database, **without writing code for you**. Follow these steps to connect the systems.

---

## Integration Points

### 1. Replace Static Patient Data with Database Queries

**Current State:**
- `mwl.py` has hardcoded `PATIENTS` list (lines 24-46)

**What to Change:**
- Remove the static `PATIENTS` list
- Import your Flask app and models (`Patient`, `Appointment`)
- Query database for scheduled appointments
- Convert database records to MWL format

**Steps:**
1. Import your Flask app factory: `from app import create_app`
2. Create app context: `app = create_app()` and `with app.app_context():`
3. Import models: `from app.models import Patient, Appointment`
4. Query today's appointments: Filter `Appointment` by `date = today` and `status`
5. Join with `Patient` model to get patient details
6. Map database fields to MWL format:
   - `Patient.id` → `patient_id`
   - `Patient.first_name + last_name` → `name`
   - `Patient.birth_date` → calculate `age`
   - `Patient.gender` → `gender`
   - `Appointment.doctor` → use for physician name
   - `Appointment.department` → use for study type
   - Generate `accession` number (or add to Appointment model)
   - Combine `Appointment.date` + `Appointment.time` → `scheduled_time`

**Where to Modify:**
- Replace `PATIENTS` list initialization
- Modify `handle_mwl_find()` function to query database instead of static list
- Update `send_mwl()` route to mark appointments in database

---

### 2. Store MWL Send Status in Database

**Current State:**
- Uses `patient['sent'] = True` flag in memory

**What to Change:**
- Add field to `Appointment` model or create new status tracking
- Store MWL sent status in database

**Steps:**
1. **Option A**: Add `mwl_sent` boolean field to `Appointment` model
   - Create migration: `flask db migrate -m "Add mwl_sent to appointments"`
   - Apply: `flask db upgrade`
   
2. **Option B**: Use existing `status` field
   - Add new status value like `'MWL_Sent'` or `'Ready_For_Scan'`
   - Update status when MWL is sent

3. Update `send_mwl()` route:
   - Find appointment by patient_id
   - Set `mwl_sent = True` or update status
   - Commit to database

**Where to Modify:**
- `app/models/appointment.py` - Add field
- `mwl.py` - Update `send_mwl()` route to save to database
- `handle_mwl_find()` - Query only appointments where `mwl_sent = True`

---

### 3. Store Received DICOM Images in Database

**Current State:**
- Images saved to `./received/` folder
- Thumbnails stored in memory (`RECEIVED_IMAGES` dict)

**What to Change:**
- Create database models for DICOM studies/series/images
- Store file paths and metadata in database
- Link images to patients via PatientID

**Steps:**
1. **Create New Models** (in `app/models/`):
   - `DicomStudy` model:
     - Fields: `study_instance_uid`, `patient_id` (FK), `study_date`, `study_description`, `accession_number`
   - `DicomSeries` model:
     - Fields: `series_instance_uid`, `study_id` (FK), `modality`, `series_description`, `body_part`
   - `DicomImage` model:
     - Fields: `sop_instance_uid`, `series_id` (FK), `file_path`, `thumbnail_path`, `image_number`

2. **Update `handle_store()` function**:
   - Parse DICOM dataset for StudyInstanceUID, SeriesInstanceUID, SOPInstanceUID
   - Find or create Study → Series → Image records
   - Link to Patient via PatientID
   - Store file path (keep files in `./received/` or move to organized structure)
   - Save thumbnail path
   - Commit to database

3. **Update Web Interface**:
   - Query database for images instead of `RECEIVED_IMAGES` dict
   - Join with Patient model to show patient names
   - Display thumbnails from database paths

**Where to Modify:**
- Create new model files: `app/models/dicom_study.py`, `dicom_series.py`, `dicom_image.py`
- Update `mwl.py` `handle_store()` function
- Update Flask route `/` to query database

---

### 4. Store Real Measurements from DICOM

**Current State:**
- Hardcoded measurements: `"Liver: 12.5 cm | Gallbladder: Normal..."`

**What to Change:**
- Parse DICOM Structured Reports (SR) if machine sends them
- Or parse measurement annotations from image DICOM tags
- Store in database

**Steps:**
1. **Create Measurement Model**:
   - `Measurement` model:
     - Fields: `study_id` (FK), `measurement_type`, `value`, `unit`, `body_part`, `notes`

2. **Parse DICOM SR** (if machine sends Structured Reports):
   - Check for SR SOP Class in received DICOM
   - Parse ContentSequence for measurements
   - Extract values, units, body parts

3. **Or Parse Image Tags**:
   - Some machines store measurements in DICOM tags
   - Look for tags like `(0018,11xx)` series or `(0040,0275)` measurement sequences
   - Extract and store

4. **Update Web Interface**:
   - Query measurements from database
   - Display grouped by study/patient

**Where to Modify:**
- Create `app/models/measurement.py`
- Update `handle_store()` to detect and parse SR or measurement tags
- Update web interface to query database

---

### 5. Add Authentication to Web Interface

**Current State:**
- No authentication - anyone can access

**What to Change:**
- Add Flask-Login authentication
- Protect routes
- Add user roles (receptionist, doctor, admin)

**Steps:**
1. **Create User Model** (if not exists):
   - Fields: `id`, `username`, `password_hash`, `role`

2. **Use Flask-Login**:
   - Initialize in `app/extensions.py`
   - Create login route
   - Add `@login_required` decorator to routes

3. **Update `mwl.py`**:
   - Import Flask-Login
   - Add login route
   - Protect `/` and `/send_mwl` routes
   - Show user info in web interface

**Where to Modify:**
- `app/models/user.py` (create if needed)
- `mwl.py` - Add login routes and decorators
- Web interface HTML - Add login form

---

### 6. Organize File Structure

**Current State:**
- All code in single `mwl.py` file
- Images saved to `./received/`

**What to Change:**
- Move MWL functionality to proper modules
- Organize DICOM file storage

**Steps:**
1. **Create Service Module**:
   - `app/services/mwl_service.py` - MWL query logic
   - `app/services/dicom_storage_service.py` - Image storage logic

2. **Create Routes**:
   - `app/routes/mwl_web.py` - Web interface routes
   - Keep DICOM servers in separate file or service

3. **File Storage Structure**:
   - Create: `dicom_storage/studies/YYYY/MM/DD/` structure
   - Or: `dicom_storage/{patient_id}/{study_date}/`
   - Store thumbnails in separate `thumbnails/` folder

**Where to Modify:**
- Refactor `mwl.py` into multiple files
- Update imports
- Update file paths in storage functions

---

### 7. Configuration Management

**Current State:**
- Hardcoded ports, AE titles, paths

**What to Change:**
- Move to config file or environment variables

**Steps:**
1. **Add to `app/config.py`**:
   - `MWL_PORT = 11112`
   - `STORAGE_PORT = 11113`
   - `MWL_AE_TITLE = 'STORESCP'`
   - `DICOM_STORAGE_PATH = 'dicom_files'`
   - `THUMBNAIL_STORAGE_PATH = 'thumbnails'`

2. **Update `mwl.py`**:
   - Import config
   - Use config values instead of hardcoded

**Where to Modify:**
- `app/config.py` - Add DICOM settings
- `mwl.py` - Replace hardcoded values with config

---

### 8. Error Handling & Logging

**Current State:**
- Basic logging to file

**What to Change:**
- Better error handling
- Structured logging
- Database logging for DICOM operations

**Steps:**
1. **Add Error Handling**:
   - Try-catch blocks around database operations
   - Handle DICOM parsing errors gracefully
   - Return proper error responses

2. **Enhanced Logging**:
   - Use `structlog` (already in dependencies)
   - Log all MWL queries
   - Log all received images
   - Log errors with context

3. **Database Audit**:
   - Use existing `AuditLog` model
   - Log MWL sends, image receives, errors

**Where to Modify:**
- Add error handling throughout `mwl.py`
- Update logging configuration
- Add audit log entries

---

### 9. Testing Integration

**Steps:**
1. **Test Database Queries**:
   - Create test patients and appointments
   - Verify MWL returns correct data
   - Check database updates

2. **Test Image Storage**:
   - Send test DICOM file
   - Verify database records created
   - Check file paths correct

3. **Test Web Interface**:
   - Login works
   - Patient list loads from database
   - Images display correctly

---

### 10. Migration Strategy

**Recommended Approach:**

1. **Phase 1: Database Models**
   - Create DICOM models
   - Add `mwl_sent` field to Appointment
   - Run migrations

2. **Phase 2: Query Integration**
   - Replace static PATIENTS with database queries
   - Test MWL server still works

3. **Phase 3: Storage Integration**
   - Update `handle_store()` to save to database
   - Test image receiving

4. **Phase 4: Web Interface**
   - Update routes to use database
   - Add authentication
   - Test end-to-end

5. **Phase 5: Refactoring**
   - Move code to proper modules
   - Clean up structure
   - Add error handling

---

## Key Files to Modify

### Database Models
- `app/models/appointment.py` - Add `mwl_sent` field
- `app/models/dicom_study.py` - New file
- `app/models/dicom_series.py` - New file  
- `app/models/dicom_image.py` - New file
- `app/models/measurement.py` - New file (optional)

### Configuration
- `app/config.py` - Add DICOM settings

### MWL File
- `mwl.py` - Multiple functions need updates:
  - Remove `PATIENTS` list
  - Update `handle_mwl_find()` - Query database
  - Update `send_mwl()` - Save to database
  - Update `handle_store()` - Save to database
  - Update web routes - Query database

### Services (if refactoring)
- `app/services/mwl_service.py` - New file
- `app/services/dicom_storage_service.py` - New file

---

## Database Schema Additions Needed

### Appointment Model
- Add: `mwl_sent` (Boolean, default=False)

### New Models Needed

**DicomStudy:**
- `id` (Integer, PK)
- `study_instance_uid` (String, unique)
- `patient_id` (String, FK → patients.id)
- `study_date` (Date)
- `study_description` (String)
- `accession_number` (String)
- `created_at`, `updated_at` (Timestamps)

**DicomSeries:**
- `id` (Integer, PK)
- `series_instance_uid` (String, unique)
- `study_id` (Integer, FK → dicom_studies.id)
- `modality` (String)
- `series_description` (String)
- `body_part` (String)
- `created_at`, `updated_at` (Timestamps)

**DicomImage:**
- `id` (Integer, PK)
- `sop_instance_uid` (String, unique)
- `series_id` (Integer, FK → dicom_series.id)
- `file_path` (String)
- `thumbnail_path` (String)
- `image_number` (Integer)
- `created_at`, `updated_at` (Timestamps)

---

## Important Considerations

### Performance
- Database queries in `handle_mwl_find()` should be fast
- Consider indexing on `Appointment.date` and `mwl_sent`
- Image storage - consider async processing for thumbnails

### Data Consistency
- Handle case where patient doesn't exist in database
- Handle duplicate DICOM receives
- Handle MWL queries for non-existent patients

### Security
- Validate DICOM data before storing
- Sanitize file paths
- Limit file sizes
- Validate PatientID matches database

### Backup
- DICOM files are important - ensure backups
- Database backups should include DICOM metadata
- Consider cloud storage for DICOM files

---

## Testing Checklist

- [ ] MWL server returns patients from database
- [ ] Sending MWL updates database correctly
- [ ] Received images saved to database
- [ ] Images linked to correct patients
- [ ] Thumbnails generated and stored
- [ ] Web interface shows database data
- [ ] Authentication works
- [ ] Error handling works
- [ ] Multiple machines can connect
- [ ] Performance is acceptable

---

## Summary

**Main Integration Tasks:**

1. ✅ Replace static PATIENTS with database queries
2. ✅ Store MWL send status in Appointment model
3. ✅ Create DICOM models (Study, Series, Image)
4. ✅ Store received images in database
5. ✅ Link images to patients
6. ✅ Update web interface to use database
7. ✅ Add authentication
8. ✅ Move configuration to config file
9. ✅ Add error handling
10. ✅ Refactor code structure

**Start with:** Database models and queries, then storage, then web interface updates.

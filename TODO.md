# OB/GYN RIS & Ultrasound Reporting System – Implementation TODO

**Source:** `todo.pdf` (FINAL – MonEcho-Equivalent specification)  
**Rule:** Implement strictly as written. Any deviation requires formal validation.

---

## 0. Scope & Authority

- [x] Document adopted as authoritative spec for the project.
- [ ] Formal change/validation process defined for any future deviation.

---

## 1. Fundamental Rules (Non-Negotiable)

| Rule | Status | Notes |
|------|--------|--------|
| One Visit = One Study = One Report | 🔲 To do | Enforce in data model and APIs (Visit/Order → Study → Report 1:1). |
| No manual patient re-entry on ultrasound devices | 🔲 To do | Rely on MWL only; document device config; no manual entry UI on devices. |
| AccessionNumber is immutable and unique | ✅ Done | Set on first “send to MWL”; stored on Appointment; used in MWL and Report. |
| Reports are structured and locked after validation | 🟡 Partial | Lifecycle draft → validated → archived; validate endpoint; delete blocked when validated/archived. Structured templates TBD. |
| Secretary and physician responsibilities strictly separated | 🟡 Partial | RBAC exists (receptionist/doctor/technician); clarify secretary vs receptionist and lock workflows. |

---

## 2. Complete Workflow

| Step | Owner | Status | Notes |
|------|--------|--------|--------|
| Patient → Appointment → Visit (Order creation) | Secretary | 🟡 Partial | Patient + Appointment exist; add explicit **Visit/Order** and link to AccessionNumber. |
| AccessionNumber generation → MWL publication | System | 🔲 To do | Generate AccessionNumber on order; publish in MWL with required tags. |
| MWL query → exam → DICOM send | Ultrasound (Samsung/GE) | 🟡 Partial | MWL SCP implemented; device config and validation needed. |
| DICOM Storage → automatic study matching | Server | 🟡 Partial | Storage SCP + DicomImage; match by AccessionNumber/StudyInstanceUID. |
| Image review → structured report → validation → PDF | Physician | 🟡 Partial | Reporting API + PDF exist; add structured templates and validation lock. |

---

## 3. DICOM Services (Mandatory)

| Service | Status | Notes |
|--------|--------|--------|
| Modality Worklist (MWL) SCP | ✅ Done | Implemented; appointments/patients in MWL. |
| Storage SCP (images + cine loops) | ✅ Done | C-STORE implemented; store and link to study. |
| MPPS (optional but recommended) | 🔲 To do | Not implemented; add for exam status tracking. |
| MWL SCU + Storage SCU on each ultrasound | — | Device/license configuration; document in deployment. |

---

## 4. Mandatory MWL & Matching Fields

| DICOM Tag | Purpose | Status |
|-----------|---------|--------|
| PatientName | Patient identification | ✅ In MWL |
| PatientID | Internal unique identifier | ✅ In MWL |
| PatientBirthDate | DOB | ✅ In MWL |
| PatientSex | Gender | ✅ In MWL |
| **AccessionNumber** | Study matching key | ✅ Done – generated on send-mwl, exposed in MWL |
| RequestedProcedureID | Exam request identifier | ✅ Done – set on send-mwl, in MWL |
| ScheduledProcedureStepID | Visit identifier | ✅ Done – set on send-mwl, in MWL |
| StudyDescription | OB/GYN exam type | 🟡 Partial – can map from appointment/department |

---

## 5. Reporting Engine (Strictly Structured)

| Requirement | Status | Notes |
|-------------|--------|--------|
| Template-only reporting (free text limited to comments) | 🔲 To do | Define and enforce OB/GYN templates. |
| OB templates: 1st trimester, morphology, growth, BPP | 🔲 To do | Add template definitions and UI/API. |
| GYN templates: pelvic, TVUS, follicular monitoring | 🔲 To do | Add template definitions and UI/API. |
| Automatic GA, EDD, percentiles | 🔲 To do | Implement calculators and expose in report. |
| Mandatory fields enforced before validation | 🔲 To do | Validation step that blocks “Validated” until required fields set. |
| Languages: English & French | 🔲 To do | Template and UI strings in both languages. |

---

## 6. Report Lifecycle Control

| State | Status | Notes |
|-------|--------|--------|
| Draft → Validated → Archived | ✅ Done | Report.lifecycle_state; POST /api/reports/<id>/validate. |
| No modification after validation | ✅ Done | Delete report blocked when validated/archived. |
| Correction = new version + audit trail | 🔲 To do | Versioning and audit log for report changes. |

---

## 7. PDF & Branding Rules

| Requirement | Status | Notes |
|-------------|--------|--------|
| Clinic logo and header mandatory | 🔲 To do | Configurable logo/header in PDF (config or admin). |
| Physician identity and digital signature | 🔲 To do | Store physician info and signature; render in PDF. |
| Date/time and AccessionNumber visible | 🟡 Partial | Date in PDF; ensure AccessionNumber in header/footer. |

---

## 8. Patient Report Delivery

| Channel | Status | Notes |
|---------|--------|--------|
| Paper printing supported | 🟡 Partial | PDF exists; document print workflow. |
| WhatsApp delivery via secure expiring link (OTP mandatory) | 🔲 To do | Generate link + OTP; integrate WhatsApp; expiry and audit. |

---

## 9. Security, Audit & Compliance

| Requirement | Status | Notes |
|-------------|--------|--------|
| Role-based access control (RBAC) | ✅ Done | Roles and decorators in place. |
| Full audit log (create, edit, validate, export) | 🟡 Partial | AuditLog model + log_audit(); used for validate report and send_mwl; extend to create/edit/export as needed. |
| HTTPS only, encrypted storage | 🟡 Partial | HTTPS via Nginx/Certbot; enforce in config; document storage encryption. |
| No hard deletion of medical data | ✅ Done | Soft delete (deleted_at) for Patient and Appointment; delete blocked for validated/archived reports. |

---

## 10. Backup & Disaster Recovery

| Requirement | Status | Notes |
|-------------|--------|--------|
| Daily automated backups (DB + DICOM files) | 🔲 To do | Scripts/cron for DB dump and DICOM storage backup. |
| Restore procedure documented and tested | 🔲 To do | Write restore runbook and test periodically. |

---

## 11. Acceptance & Go-Live Criteria

| Criterion | Status |
|-----------|--------|
| MWL visible on Samsung and GE | 🔲 To do – validate on real devices |
| Images correctly matched by AccessionNumber | 🔲 To do – end-to-end test |
| Structured report validation enforced | 🔲 To do |
| Secure report delivery functional | 🔲 To do |

---

## Summary

- **Done:** MWL SCP, Storage SCP, RBAC, basic Reporting API and PDF, patient/appointment/admin/DICOM models, auth, deployment.
- **Next priorities (in order):**
  1. AccessionNumber generation and use everywhere (Visit/Order, MWL, DICOM, Report).
  2. Visit/Order model and “One Visit = One Study = One Report” enforcement.
  3. Report lifecycle (Draft/Validated/Archived) and no-edit-after-validation.
  4. Structured OB/GYN templates and mandatory-field validation.
  5. PDF branding (logo, header, physician signature) and AccessionNumber on PDF.
  6. Audit log, soft delete, backup/restore, then WhatsApp delivery and MPPS.

*Last updated from `todo.pdf` spec.*

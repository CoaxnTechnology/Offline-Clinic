"""
Super Admin routes.

Provides multi‑clinic management so each clinic has isolated data.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Admin, Clinic
from app.utils.audit import log_audit
from app.services.email_service import send_welcome_email
from app.config import Config
import secrets
from datetime import datetime, timedelta


super_admin_bp = Blueprint("super_admin", __name__, url_prefix="/api/super-admin")


from typing import Optional


def _current_admin() -> Optional[Admin]:
    try:
        user_id = int(get_jwt_identity())
    except Exception:
        return None
    return Admin.query.get(user_id)


def _require_super_admin(admin: Optional[Admin]):
    if not admin or not admin.is_super_admin:
        return jsonify({"success": False, "error": "Super admin only"}), 403
    return None


@super_admin_bp.route("/clinics", methods=["GET"])
@jwt_required()
def list_clinics():
    """
    Minimal clinics list for super admin.
    """
    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    clinics = Clinic.query.all()
    data = []
    for c in clinics:
        data.append(
            {
                "id": c.id,
                "name": c.name,
                "address": c.address,
                "phone": c.phone,
                "email": c.email,
                "license_key": c.license_key,
                "is_active": c.is_active,
            }
        )

    return jsonify({"success": True, "data": data}), 200


@super_admin_bp.route("/clinics", methods=["POST"])
@jwt_required()
def create_clinic_with_doctor():
    """
    Create a new clinic + one doctor, with isolated data.

    Access: super admin only.

    Body JSON:
    {
      "hospital_name": "Sunshine Hospital",    # required
      "license_name": "SUN-0001",             # required, unique
      "doctor_name": "Dr. Sunshine",           # required
      "contact_number": "+91 99999 99999",     # required
      "email": "doctor@sunshine.com",          # required, unique
      "clinic_address": "123 Medical Rd"       # optional
    }

    AE Title is auto-generated.
    Returns clinic + doctor info and a set-password link.
    """
    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    data = request.get_json() or {}

    # Validate required fields
    hospital_name = (data.get("hospital_name") or "").strip()
    license_name = (data.get("license_name") or "").strip()
    doctor_name = (data.get("doctor_name") or "").strip()
    contact_number = (data.get("contact_number") or "").strip()
    email = (data.get("email") or "").strip()
    clinic_address = (data.get("clinic_address") or "").strip() or None

    if not hospital_name or not license_name or not doctor_name or not contact_number or not email:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "hospital_name, license_name, doctor_name, contact_number and email are required",
                }
            ),
            400,
        )

    if Clinic.query.filter_by(license_key=license_name).first():
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Clinic with this license_name already exists",
                }
            ),
            400,
        )

    # Auto-generate username from doctor_name (e.g. "Dr. Sunshine" -> "dr.sunshine")
    username = doctor_name.lower().replace(" ", "").replace(".", "")
    # Ensure unique username
    base_username = username
    counter = 1
    while Admin.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1

    if Admin.query.filter_by(email=email).first():
        return (
            jsonify(
                {"success": False, "error": "Admin with this email already exists"}
            ),
            400,
        )

    try:
        # 1) Create clinic (AE Title will be set after we get clinic.id)
        clinic = Clinic(
            name=hospital_name,
            address=clinic_address,
            phone=contact_number,
            email=email,
            license_key=license_name,
            max_doctors=1,
            is_active=True,
        )
        db.session.add(clinic)
        db.session.flush()  # get clinic.id

        # Auto-generate AE Title for DICOM: CLINIC1_DICOM, CLINIC2_DICOM, etc.
        ae_title_prefix = "CLINIC"
        clinic.dicom_ae_title = f"{ae_title_prefix}{clinic.id}_DICOM"
        db.session.flush()

        # 2) Create first doctor for this clinic
        token = secrets.token_urlsafe(32)
        temp_password = secrets.token_urlsafe(16)

        doctor = Admin(
            clinic_id=clinic.id,
            username=username,
            email=email,
            first_name=doctor_name,
            last_name="",
            phone=contact_number,
            role="doctor",
            is_active=False,  # will activate after setting password
            is_super_admin=False,
            reset_token=token,
            reset_token_expiry=datetime.utcnow() + timedelta(days=7),
        )
        doctor.set_password(temp_password)

        db.session.add(doctor)
        db.session.commit()

        # 3) Send welcome email with set-password link
        base_url = (
            Config.FRONTEND_BASE_URL
            or Config.PUBLIC_BASE_URL
            or "http://localhost:8080"
        )
        reset_link = f"{base_url.rstrip('/')}/reset-password/{token}"
        send_welcome_email(
            email=doctor.email,
            username=doctor.username,
            role=doctor.role,
            set_password_link=reset_link,
            clinic_name=clinic.name,
        )

        # 4) Audit log
        log_audit(
            "clinic",
            "create",
            user_id=current.id,
            entity_id=str(clinic.id),
            details={"clinic_id": clinic.id, "doctor_id": doctor.id},
        )

        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "clinic": {
                            "id": clinic.id,
                            "hospital_name": clinic.name,
                            "license_name": clinic.license_key,
                            "clinic_address": clinic.address,
                            "contact_number": clinic.phone,
                            "email": clinic.email,
                            "ae_title": clinic.dicom_ae_title,
                            "is_active": clinic.is_active,
                        },
                        "doctor": {
                            "id": doctor.id,
                            "username": doctor.username,
                            "doctor_name": doctor.first_name,
                            "email": doctor.email,
                            "contact_number": doctor.phone,
                            "role": doctor.role,
                            "clinic_id": doctor.clinic_id,
                            "is_active": doctor.is_active,
                        },
                        "set_password_link": reset_link,
                    },
                    "message": "Clinic and doctor created successfully",
                }
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Failed to create clinic: {str(e)}",
                }
            ),
            500,
        )


@super_admin_bp.route("/health", methods=["GET"])
@jwt_required()
def super_admin_health():
    """
    Simple health check for super admin API.
    """
    current = _current_admin()
    if not current:
        return jsonify({"success": False, "error": "User not found"}), 404
    if not current.is_super_admin:
        return jsonify({"success": False, "error": "Super admin only"}), 403

    return jsonify({"success": True, "message": "Super admin API OK"}), 200


@super_admin_bp.route("/cleanup/patients", methods=["DELETE"])
@jwt_required()
def cleanup_all_patients():
    """
    Delete all patients and their related data.
    WARNING: This will delete ALL patients, appointments, visits, DICOM images, prescriptions.
    Only super admin can access this.
    """
    from app.models import Patient, Appointment, Visit, DicomImage, Prescription, Report

    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    try:
        # Count before deletion
        patient_count = Patient.query.count()
        appointment_count = Appointment.query.count()
        visit_count = Visit.query.count()
        dicom_count = DicomImage.query.count()
        prescription_count = Prescription.query.count()
        report_count = Report.query.count()

        # Delete in correct order (foreign keys first)
        Report.query.delete()
        DicomImage.query.delete()
        Prescription.query.delete()
        Visit.query.delete()
        Appointment.query.delete()
        Patient.query.delete()

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "All patient data cleaned successfully",
                "deleted": {
                    "patients": patient_count,
                    "appointments": appointment_count,
                    "visits": visit_count,
                    "dicom_images": dicom_count,
                    "prescriptions": prescription_count,
                    "reports": report_count,
                },
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Cleanup failed: {str(e)}"}), 500


@super_admin_bp.route("/cleanup/appointments", methods=["DELETE"])
@jwt_required()
def cleanup_all_appointments():
    """
    Delete all appointments and their related data.
    WARNING: This will delete ALL appointments, visits, DICOM images, prescriptions.
    Only super admin can access this.
    """
    from app.models import Appointment, Visit, DicomImage, Prescription, Report

    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    try:
        appointment_count = Appointment.query.count()
        visit_count = Visit.query.count()
        dicom_count = DicomImage.query.count()
        prescription_count = Prescription.query.count()
        report_count = Report.query.count()

        Report.query.delete()
        DicomImage.query.delete()
        Prescription.query.delete()
        Visit.query.delete()
        Appointment.query.delete()

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "All appointments cleaned successfully",
                "deleted": {
                    "appointments": appointment_count,
                    "visits": visit_count,
                    "dicom_images": dicom_count,
                    "prescriptions": prescription_count,
                    "reports": report_count,
                },
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Cleanup failed: {str(e)}"}), 500

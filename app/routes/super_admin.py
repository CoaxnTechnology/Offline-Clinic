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
      "clinic": {
        "name": "Sunshine Hospital",        # required
        "address": "123 Medical Rd",        # optional
        "phone": "+91 99999 99999",         # optional
        "email": "info@sunshine.com",       # optional
        "license_key": "SUN-0001"           # required, unique
      },
      "doctor": {
        "username": "drsunshine",           # required, unique
        "email": "doctor@sunshine.com",     # required, unique
        "first_name": "Sunshine",           # required
        "last_name": "Doctor",              # required
        "phone": "+91 88888 88888"          # optional
      }
    }

    Returns clinic + doctor info and a set‑password link is emailed to the doctor.
    """
    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    data = request.get_json() or {}
    clinic_data = data.get("clinic") or {}
    doctor_data = data.get("doctor") or {}

    # Validate clinic fields
    name = (clinic_data.get("name") or "").strip()
    license_key = (clinic_data.get("license_key") or "").strip()
    if not name or not license_key:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "clinic.name and clinic.license_key are required",
                }
            ),
            400,
        )

    if Clinic.query.filter_by(license_key=license_key).first():
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Clinic with this license_key already exists",
                }
            ),
            400,
        )

    # Validate doctor fields
    username = (doctor_data.get("username") or "").strip()
    email = (doctor_data.get("email") or "").strip()
    first_name = (doctor_data.get("first_name") or "").strip()
    last_name = (doctor_data.get("last_name") or "").strip()
    phone = (doctor_data.get("phone") or "").strip() or None

    if not username or not email or not first_name or not last_name:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "doctor.username, doctor.email, doctor.first_name and doctor.last_name are required",
                }
            ),
            400,
        )

    if Admin.query.filter_by(username=username).first():
        return (
            jsonify(
                {"success": False, "error": "Admin with this username already exists"}
            ),
            400,
        )
    if Admin.query.filter_by(email=email).first():
        return (
            jsonify(
                {"success": False, "error": "Admin with this email already exists"}
            ),
            400,
        )

    try:
        # 1) Create clinic
        clinic = Clinic(
            name=name,
            address=clinic_data.get("address"),
            phone=clinic_data.get("phone"),
            email=clinic_data.get("email"),
            license_key=license_key,
            max_doctors=clinic_data.get("max_doctors") or 1,
            is_active=True,
        )
        db.session.add(clinic)
        db.session.flush()  # get clinic.id

        # 2) Create first doctor for this clinic
        token = secrets.token_urlsafe(32)
        temp_password = secrets.token_urlsafe(16)

        doctor = Admin(
            clinic_id=clinic.id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role="doctor",
            is_active=False,  # will activate after setting password
            is_super_admin=False,
            reset_token=token,
            reset_token_expiry=datetime.utcnow() + timedelta(days=7),
        )
        doctor.set_password(temp_password)

        db.session.add(doctor)
        db.session.commit()

        # 3) Send welcome email with set‑password link
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
                        "clinic": clinic.to_dict(),
                        "doctor": {
                            "id": doctor.id,
                            "username": doctor.username,
                            "email": doctor.email,
                            "first_name": doctor.first_name,
                            "last_name": doctor.last_name,
                            "phone": doctor.phone,
                            "role": doctor.role,
                            "clinic_id": doctor.clinic_id,
                            "is_active": doctor.is_active,
                        },
                        "set_password_link": reset_link,
                    },
                    "message": "Clinic and first doctor created successfully",
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

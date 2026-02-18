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
    List clinics with doctor info for super admin.
    """
    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    clinics = Clinic.query.all()
    data = []
    for c in clinics:
        doctors = Admin.query.filter_by(clinic_id=c.id, role="doctor").all()

        # Flatten first doctor info
        doctor_info = None
        if doctors:
            d = doctors[0]
            doctor_info = {
                "id": d.id,
                "username": d.username,
                "first_name": d.first_name,
                "last_name": d.last_name,
                "email": d.email,
                "phone": d.phone,
                "is_active": d.is_active,
            }

        # Build logo URL
        logo_url = None
        if c.logo_path:
            logo_url = f"/api/super-admin/clinics/{c.id}/logo"

        data.append(
            {
                "id": c.id,
                "hospital_name": c.name,
                "clinic_address": c.address,
                "contact_number": c.phone,
                "email": c.email,
                "license_name": c.license_key,
                "ae_title": c.dicom_ae_title,
                "is_active": c.is_active,
                "logo_path": c.logo_path,
                "logo_url": logo_url,
                "doctor": doctor_info,
            }
        )

    return jsonify({"success": True, "data": data}), 200


@super_admin_bp.route("/clinics/<int:clinic_id>", methods=["GET"])
@jwt_required()
def get_clinic(clinic_id):
    """
    Get clinic details with doctor info.
    """
    current = _current_admin()

    # Super admin can view any clinic, doctor can only view their own
    if not current.is_super_admin:
        if current.clinic_id != clinic_id:
            return jsonify({"success": False, "error": "Not found"}), 404

    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({"success": False, "error": "Clinic not found"}), 404

    doctors = Admin.query.filter_by(clinic_id=clinic.id, role="doctor").all()

    doctor_info = None
    if doctors:
        d = doctors[0]
        doctor_info = {
            "id": d.id,
            "username": d.username,
            "first_name": d.first_name,
            "last_name": d.last_name,
            "email": d.email,
            "phone": d.phone,
            "is_active": d.is_active,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }

    # Build logo URL
    logo_url = None
    if clinic.logo_path:
        logo_url = f"/api/super-admin/clinics/{clinic.id}/logo"

    return jsonify(
        {
            "success": True,
            "data": {
                "id": clinic.id,
                "hospital_name": clinic.name,
                "clinic_address": clinic.address,
                "contact_number": clinic.phone,
                "email": clinic.email,
                "license_name": clinic.license_key,
                "ae_title": clinic.dicom_ae_title,
                "is_active": clinic.is_active,
                "logo_path": clinic.logo_path,
                "logo_url": logo_url,
                "header_text": clinic.header_text,
                "footer_text": clinic.footer_text,
                "doctor": doctor_info,
                "created_at": clinic.created_at.isoformat()
                if clinic.created_at
                else None,
            },
        }
    ), 200


@super_admin_bp.route("/clinics/<int:clinic_id>", methods=["PUT"])
@jwt_required()
def update_clinic(clinic_id):
    """Update clinic details. Access: super admin or doctor of the clinic."""
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app

    current = _current_admin()

    # Super admin can update any clinic, doctor can only update their own clinic
    if not current.is_super_admin:
        if current.clinic_id != clinic_id:
            return jsonify(
                {"success": False, "error": "Not authorized to update this clinic"}
            ), 403
        # Doctors can only update certain fields
        is_doctor = True
    else:
        is_doctor = False

    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({"success": False, "error": "Clinic not found"}), 404

    # Check if multipart form data (logo upload)
    if request.content_type and "multipart/form-data" in request.content_type:
        # Handle multipart form data
        hospital_name = request.form.get("hospital_name")
        clinic_address = request.form.get("clinic_address")
        contact_number = request.form.get("contact_number")
        email = request.form.get("email")
        header_text = request.form.get("header_text")
        footer_text = request.form.get("footer_text")
        license_name = request.form.get("license_name")
        is_active = request.form.get("is_active")
        remove_logo = request.form.get("remove_logo", "").lower() == "true"
        logo_file = request.files.get("logo")

        # Super admin can update all fields, doctors can only update limited fields
        if is_doctor:
            if hospital_name:
                clinic.name = hospital_name
            if clinic_address is not None:
                clinic.address = clinic_address
            if contact_number is not None:
                clinic.phone = contact_number
            if email is not None:
                clinic.email = email
        else:
            if hospital_name:
                clinic.name = hospital_name
            if license_name:
                existing = Clinic.query.filter(
                    Clinic.license_key == license_name, Clinic.id != clinic_id
                ).first()
                if existing:
                    return jsonify(
                        {"success": False, "error": "License name already exists"}
                    ), 400
                clinic.license_key = license_name
            if clinic_address is not None:
                clinic.address = clinic_address
            if contact_number is not None:
                clinic.phone = contact_number
            if email is not None:
                clinic.email = email
            if is_active is not None:
                clinic.is_active = is_active.lower() == "true"

        # Common fields
        if header_text is not None:
            clinic.header_text = header_text
        if footer_text is not None:
            clinic.footer_text = footer_text

        # Handle logo
        if remove_logo and clinic.logo_path:
            old_path = os.path.join(
                current_app.config.get("PROJECT_ROOT", ""), clinic.logo_path
            )
            if os.path.exists(old_path):
                os.remove(old_path)
            clinic.logo_path = None

        if logo_file and logo_file.filename:
            allowed_extensions = {".jpg", ".jpeg", ".png", ".svg", ".webp"}
            ext = os.path.splitext(secure_filename(logo_file.filename))[1].lower()
            if ext not in allowed_extensions:
                return jsonify(
                    {
                        "success": False,
                        "error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
                    }
                ), 400

            upload_folder = os.path.join(
                current_app.config.get("PROJECT_ROOT", ""), "clinic_logos"
            )
            os.makedirs(upload_folder, exist_ok=True)

            # Remove old logo if exists
            if clinic.logo_path:
                old_path = os.path.join(
                    current_app.config.get("PROJECT_ROOT", ""), clinic.logo_path
                )
                if os.path.exists(old_path):
                    os.remove(old_path)

            filename = f"clinic_{clinic.id}_logo{ext}"
            filepath = os.path.join(upload_folder, filename)
            logo_file.save(filepath)
            clinic.logo_path = os.path.join("clinic_logos", filename)
    else:
        # Handle JSON
        data = request.get_json() or {}

        # Super admin can update all fields, doctors can only update limited fields
        if is_doctor:
            if "hospital_name" in data:
                clinic.name = data["hospital_name"]
            if "clinic_address" in data:
                clinic.address = data["clinic_address"]
            if "contact_number" in data:
                clinic.phone = data["contact_number"]
            if "email" in data:
                clinic.email = data["email"]
        else:
            if "hospital_name" in data:
                clinic.name = data["hospital_name"]
            if "license_name" in data:
                existing = Clinic.query.filter(
                    Clinic.license_key == data["license_name"], Clinic.id != clinic_id
                ).first()
                if existing:
                    return jsonify(
                        {"success": False, "error": "License name already exists"}
                    ), 400
                clinic.license_key = data["license_name"]
            if "clinic_address" in data:
                clinic.address = data["clinic_address"]
            if "contact_number" in data:
                clinic.phone = data["contact_number"]
            if "email" in data:
                clinic.email = data["email"]
            if "is_active" in data:
                clinic.is_active = bool(data["is_active"])

        # Common fields for both
        if "header_text" in data:
            clinic.header_text = data["header_text"]
        if "footer_text" in data:
            clinic.footer_text = data["footer_text"]

        # Handle logo (base64 in JSON)
        if "logo" in data and data["logo"]:
            import base64

            try:
                # Remove data:image/xxx;base64, prefix if present
                logo_data = data["logo"]
                if "," in logo_data:
                    header, logo_data = logo_data.split(",", 1)
                    # Extract extension from header (e.g., "data:image/png;base64")
                    ext = ".png"
                    if "jpeg" in header or "jpg" in header:
                        ext = ".jpg"
                    elif "svg" in header:
                        ext = ".svg"
                    elif "webp" in header:
                        ext = ".webp"
                else:
                    # Assume PNG if no header
                    ext = ".png"

                # Decode base64
                image_bytes = base64.b64decode(logo_data)

                upload_folder = os.path.join(
                    current_app.config.get("PROJECT_ROOT", ""), "clinic_logos"
                )
                os.makedirs(upload_folder, exist_ok=True)

                # Remove old logo if exists
                if clinic.logo_path:
                    old_path = os.path.join(
                        current_app.config.get("PROJECT_ROOT", ""), clinic.logo_path
                    )
                    if os.path.exists(old_path):
                        os.remove(old_path)

                filename = f"clinic_{clinic.id}_logo{ext}"
                filepath = os.path.join(upload_folder, filename)

                with open(filepath, "wb") as f:
                    f.write(image_bytes)

                clinic.logo_path = os.path.join("clinic_logos", filename)
            except Exception as e:
                return jsonify(
                    {"success": False, "error": f"Invalid logo data: {str(e)}"}
                ), 400

        # Handle remove_logo flag
        if data.get("remove_logo") == True or data.get("remove_logo") == "true":
            if clinic.logo_path:
                old_path = os.path.join(
                    current_app.config.get("PROJECT_ROOT", ""), clinic.logo_path
                )
                if os.path.exists(old_path):
                    os.remove(old_path)
                clinic.logo_path = None

    try:
        db.session.commit()
        log_audit(
            "clinic",
            "update",
            user_id=current.id,
            entity_id=str(clinic_id),
            details={},
        )

        # Get doctor info
        doctors = Admin.query.filter_by(clinic_id=clinic.id, role="doctor").all()
        doctor_info = None
        if doctors:
            d = doctors[0]
            doctor_info = {
                "id": d.id,
                "username": d.username,
                "first_name": d.first_name,
                "last_name": d.last_name,
                "email": d.email,
                "phone": d.phone,
                "is_active": d.is_active,
            }

        # Build logo URL
        logo_url = None
        if clinic.logo_path:
            logo_url = f"/api/super-admin/clinics/{clinic.id}/logo"

        return jsonify(
            {
                "success": True,
                "data": {
                    "id": clinic.id,
                    "hospital_name": clinic.name,
                    "license_name": clinic.license_key,
                    "clinic_address": clinic.address,
                    "contact_number": clinic.phone,
                    "email": clinic.email,
                    "ae_title": clinic.dicom_ae_title,
                    "is_active": clinic.is_active,
                    "logo_path": clinic.logo_path,
                    "logo_url": logo_url,
                    "header_text": clinic.header_text,
                    "footer_text": clinic.footer_text,
                    "doctor": doctor_info,
                },
                "message": "Clinic updated successfully",
            }
        ), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"success": False, "error": f"Failed to update clinic: {str(e)}"}
        ), 500


@super_admin_bp.route("/clinics/<int:clinic_id>", methods=["DELETE"])
@jwt_required()
def delete_clinic(clinic_id):
    """Hard-delete a clinic and ALL its data. Access: super admin only."""
    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({"success": False, "error": "Clinic not found"}), 404

    try:
        from app.models import (
            Patient,
            Appointment,
            Visit,
            DicomImage,
            DicomMeasurement,
            Prescription,
            Report,
            AuditLog,
        )
        from sqlalchemy import text

        clinic_name = clinic.name
        admin_ids = [a.id for a in Admin.query.filter_by(clinic_id=clinic_id).all()]
        if admin_ids:
            AuditLog.query.filter(AuditLog.user_id.in_(admin_ids)).delete()
        DicomMeasurement.query.filter_by(clinic_id=clinic_id).delete()
        DicomImage.query.filter_by(clinic_id=clinic_id).delete()
        Report.query.filter_by(clinic_id=clinic_id).delete()
        Prescription.query.filter_by(clinic_id=clinic_id).delete()
        Visit.query.filter_by(clinic_id=clinic_id).delete()
        Appointment.query.filter_by(clinic_id=clinic_id).delete()
        Patient.query.filter_by(clinic_id=clinic_id).delete()
        Admin.query.filter_by(clinic_id=clinic_id).delete()
        db.session.delete(clinic)
        db.session.commit()

        log_audit(
            "clinic",
            "delete",
            user_id=current.id,
            entity_id=str(clinic_id),
            details={"clinic_name": clinic_name},
        )
        return jsonify(
            {
                "success": True,
                "message": f"Clinic '{clinic_name}' and all its data deleted successfully",
            }
        ), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"success": False, "error": f"Failed to delete clinic: {str(e)}"}
        ), 500


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

    if (
        not hospital_name
        or not license_name
        or not doctor_name
        or not contact_number
        or not email
    ):
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
        return jsonify({"success": False, "error": f"Cleanup failed: {str(e)}"}), 500


@super_admin_bp.route("/clinics/<int:clinic_id>/logo", methods=["POST"])
@jwt_required()
def upload_clinic_logo(clinic_id):
    """
    Upload clinic logo image.
    Access: super admin only.

    Multipart form data:
        logo: Image file (jpg, png, svg, webp)
    """
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app

    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({"success": False, "error": "Clinic not found"}), 404

    if "logo" not in request.files:
        return jsonify({"success": False, "error": "No logo file provided"}), 400

    file = request.files["logo"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    allowed_extensions = {".jpg", ".jpeg", ".png", ".svg", ".webp"}
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in allowed_extensions:
        return jsonify(
            {
                "success": False,
                "error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
            }
        ), 400

    upload_folder = os.path.join(
        current_app.config.get("PROJECT_ROOT", ""), "clinic_logos"
    )
    os.makedirs(upload_folder, exist_ok=True)

    filename = f"clinic_{clinic_id}_logo{ext}"
    filepath = os.path.join(upload_folder, filename)

    try:
        file.save(filepath)

        relative_path = os.path.join("clinic_logos", filename)
        clinic.logo_path = relative_path
        db.session.commit()

        log_audit(
            "clinic",
            "upload_logo",
            user_id=current.id,
            entity_id=str(clinic_id),
            details={"filename": filename},
        )

        return jsonify(
            {
                "success": True,
                "message": "Logo uploaded successfully",
                "data": {
                    "clinic_id": clinic.id,
                    "logo_url": f"/api/super-admin/clinics/{clinic_id}/logo",
                    "logo_path": relative_path,
                },
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"success": False, "error": f"Failed to upload logo: {str(e)}"}
        ), 500


@super_admin_bp.route("/clinics/<int:clinic_id>/logo", methods=["GET"])
@jwt_required()
def get_clinic_logo(clinic_id):
    """
    Get clinic logo.
    Access: super admin only.
    """
    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({"success": False, "error": "Clinic not found"}), 404

    if not clinic.logo_path:
        return jsonify({"success": False, "error": "No logo set for this clinic"}), 404

    from flask import send_from_directory
    from app.config import Config

    logo_full_path = os.path.join(Config.PROJECT_ROOT, clinic.logo_path)
    logo_dir = os.path.dirname(logo_full_path)
    logo_filename = os.path.basename(logo_full_path)

    if not os.path.exists(logo_full_path):
        return jsonify(
            {"success": False, "error": "Logo file not found on server"}
        ), 404

    return send_from_directory(logo_dir, logo_filename)


@super_admin_bp.route("/clinics/<int:clinic_id>/logo", methods=["DELETE"])
@jwt_required()
def delete_clinic_logo(clinic_id):
    """
    Delete clinic logo.
    Access: super admin only.
    """
    import os
    from flask import current_app

    current = _current_admin()
    err = _require_super_admin(current)
    if err is not None:
        return err

    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({"success": False, "error": "Clinic not found"}), 404

    if not clinic.logo_path:
        return jsonify({"success": False, "error": "No logo set for this clinic"}), 404

    logo_full_path = os.path.join(
        current_app.config.get("PROJECT_ROOT", ""), clinic.logo_path
    )

    try:
        if os.path.exists(logo_full_path):
            os.remove(logo_full_path)

        clinic.logo_path = None
        db.session.commit()

        log_audit(
            "clinic",
            "delete_logo",
            user_id=current.id,
            entity_id=str(clinic_id),
            details={},
        )

        return jsonify({"success": True, "message": "Logo deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"success": False, "error": f"Failed to delete logo: {str(e)}"}
        ), 500


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

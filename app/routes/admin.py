from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Admin, Clinic
from app.utils.decorators import (
    get_current_clinic_id,
    verify_clinic_access,
    require_role,
)
from app.utils.audit import log_audit
from app.services.email_service import send_welcome_email
from app.config import Config
import os
import secrets
from datetime import datetime, timedelta


admin_bp = Blueprint("admin", __name__, url_prefix="/api/doctors")


def _current_admin():
    user_id = int(get_jwt_identity())
    return Admin.query.get(user_id)


@admin_bp.route("", methods=["GET"])
@jwt_required()
def list_users():
    """
    List doctors or receptionists.
    When mounted at /api/doctors -> list doctors
    When mounted at /api/receptionists -> list receptionists.
    """
    clinic_id, is_super = get_current_clinic_id()
    role = "doctor" if request.blueprint == "admin" else "receptionist"
    query = Admin.query.filter_by(role=role, is_super_admin=False)
    if not is_super and clinic_id:
        query = query.filter(Admin.clinic_id == clinic_id)
    items = []
    for a in query.all():
        items.append(
            {
                "id": a.id,
                "username": a.username,
                "first_name": a.first_name,
                "last_name": a.last_name,
                "email": a.email,
                "phone": a.phone,
                "clinic_id": a.clinic_id,
                "role": a.role,
                "is_active": a.is_active,
                "is_super_admin": a.is_super_admin,
                "last_login": a.last_login.isoformat() if a.last_login else None,
                "login_count": a.login_count,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )
    return jsonify({"success": True, "data": items}), 200


@admin_bp.route("", methods=["POST"])
@jwt_required()
def create_user():
    """
    Create doctor or receptionist for current admin's clinic.
    Body: { username, first_name, last_name, email, phone }
    """
    current = _current_admin()
    data = request.get_json() or {}

    role = "doctor" if request.blueprint == "admin" else "receptionist"
    clinic_id = current.clinic_id

    # Validate required fields
    username = (data.get("username") or "").strip()
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip() or None

    if not username:
        return jsonify({"success": False, "error": "Username is required"}), 400
    if not first_name:
        return jsonify({"success": False, "error": "First name is required"}), 400
    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400

    # Check duplicates
    if Admin.query.filter_by(username=username).first():
        return jsonify({"success": False, "error": "Username already exists"}), 400
    if Admin.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "Email already exists"}), 400
    if phone and Admin.query.filter_by(phone=phone).first():
        return jsonify({"success": False, "error": "Phone number already exists"}), 400

    user = Admin(
        username=username,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        role=role,
        is_active=False,
        is_super_admin=False,
        clinic_id=clinic_id,
        license_number=data.get("license_number"),
    )

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(days=7)
    user.set_password(secrets.token_urlsafe(16))

    db.session.add(user)
    db.session.commit()

    clinic = Clinic.query.get(clinic_id) if clinic_id else None
    clinic_name = clinic.name if clinic else None

    # Use FRONTEND_BASE_URL for set-password/reset-password links so it can point to the web app,
    # independent of PUBLIC_BASE_URL (used for PDFs and other backend URLs).
    base_url = (
        Config.FRONTEND_BASE_URL or Config.PUBLIC_BASE_URL or "http://localhost:8080"
    )
    reset_link = f"{base_url.rstrip('/')}/reset-password/{token}"

    send_welcome_email(
        email=user.email,
        username=user.username,
        role=user.role,
        set_password_link=reset_link,
        clinic_name=clinic_name,
    )

    log_audit(
        "admin",
        "create",
        user_id=current.id,
        entity_id=str(user.id),
        details={"role": role, "clinic_id": clinic_id},
    )

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "clinic_id": clinic_id,
                    "role": role,
                    "is_active": user.is_active,
                },
            }
        ),
        201,
    )


@admin_bp.route("/<int:admin_id>", methods=["GET"])
@jwt_required()
def get_user(admin_id):
    """Get doctor/receptionist by id."""
    admin = Admin.query.get(admin_id)
    if not admin or admin.is_super_admin:
        return jsonify({"success": False, "error": "User not found"}), 404

    # Clinic isolation
    clinic_id, is_super = get_current_clinic_id()
    denied = verify_clinic_access(admin, clinic_id, is_super)
    if denied:
        return denied

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "id": admin.id,
                    "username": admin.username,
                    "first_name": admin.first_name,
                    "last_name": admin.last_name,
                    "email": admin.email,
                    "phone": admin.phone,
                    "clinic_id": admin.clinic_id,
                    "role": admin.role,
                    "is_active": admin.is_active,
                    "is_super_admin": admin.is_super_admin,
                    "last_login": admin.last_login.isoformat()
                    if admin.last_login
                    else None,
                    "login_count": admin.login_count,
                    "created_at": admin.created_at.isoformat()
                    if admin.created_at
                    else None,
                },
            }
        ),
        200,
    )


@admin_bp.route("/<int:admin_id>", methods=["PUT"])
@jwt_required()
def update_user(admin_id):
    """Update doctor/receptionist info."""
    current = _current_admin()
    admin = Admin.query.get(admin_id)
    if not admin or admin.is_super_admin:
        return jsonify({"success": False, "error": "User not found"}), 404

    # Clinic isolation
    clinic_id, is_super = get_current_clinic_id()
    denied = verify_clinic_access(admin, clinic_id, is_super)
    if denied:
        return denied

    data = request.get_json() or {}

    if "first_name" in data:
        admin.first_name = data["first_name"]
    if "last_name" in data:
        admin.last_name = data["last_name"]
    if "email" in data:
        admin.email = data["email"]
    if "phone" in data:
        admin.phone = data["phone"]
    if "is_active" in data:
        admin.is_active = bool(data["is_active"])

    db.session.commit()

    log_audit(
        "admin",
        "update",
        user_id=current.id,
        entity_id=str(admin.id),
        details=data,
    )

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "id": admin.id,
                    "username": admin.username,
                    "first_name": admin.first_name,
                    "last_name": admin.last_name,
                    "email": admin.email,
                    "phone": admin.phone,
                    "clinic_id": admin.clinic_id,
                    "role": admin.role,
                    "is_active": admin.is_active,
                    "is_super_admin": admin.is_super_admin,
                },
            }
        ),
        200,
    )


@admin_bp.route("/<int:admin_id>", methods=["DELETE"])
@jwt_required()
def delete_user(admin_id):
    """Hard-delete a doctor or receptionist."""
    current = _current_admin()
    admin = Admin.query.get(admin_id)
    if not admin or admin.is_super_admin:
        return jsonify({"success": False, "error": "User not found"}), 404

    # Clinic isolation
    clinic_id, is_super = get_current_clinic_id()
    denied = verify_clinic_access(admin, clinic_id, is_super)
    if denied:
        return denied

    # Prevent deleting yourself
    if admin.id == current.id:
        return jsonify({"success": False, "error": "Cannot delete yourself"}), 400

    try:
        user_info = {"username": admin.username, "role": admin.role}
        db.session.delete(admin)
        db.session.commit()

        log_audit(
            "admin",
            "delete",
            user_id=current.id,
            entity_id=str(admin_id),
            details=user_info,
        )

        return jsonify(
            {
                "success": True,
                "message": f"{user_info['role'].capitalize()} '{user_info['username']}' deleted successfully",
            }
        ), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Failed to delete: {str(e)}"}), 500


clinic_bp = Blueprint("clinic", __name__, url_prefix="/api/clinic")


# Alias route for frontend compatibility - /api/clinics/<id>
@clinic_bp.route("/<int:clinic_id>", methods=["GET"])
@jwt_required()
def get_clinic_by_id(clinic_id):
    """
    Get clinic details by ID.
    Access: doctor (only their own clinic) or super admin.
    """
    current = _current_admin()

    # Check access - doctor can only view their own clinic
    if not current.is_super_admin:
        if current.clinic_id != clinic_id:
            return jsonify({"success": False, "error": "Not authorized"}), 403

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
        }

    logo_url = None
    if clinic.logo_path:
        logo_url = f"/api/clinics/{clinic.id}/logo"

    return jsonify(
        {
            "success": True,
            "data": {
                "id": clinic.id,
                "name": clinic.name,
                "address": clinic.address,
                "phone": clinic.phone,
                "email": clinic.email,
                "license_key": clinic.license_key,
                "dicom_ae_title": clinic.dicom_ae_title,
                "is_active": clinic.is_active,
                "logo_path": clinic.logo_path,
                "logo_url": logo_url,
                "header_text": clinic.header_text,
                "footer_text": clinic.footer_text,
                "doctor": doctor_info,
            },
        }
    ), 200


@clinic_bp.route("/<int:clinic_id>/logo", methods=["GET"])
@jwt_required()
def get_clinic_logo_by_id(clinic_id):
    """Get clinic logo by clinic ID."""
    current = _current_admin()

    # Check access
    if not current.is_super_admin:
        if current.clinic_id != clinic_id:
            return jsonify({"success": False, "error": "Not authorized"}), 403

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


# PUT endpoint for /api/clinics/<id> - for frontend compatibility
@clinic_bp.route("/<int:clinic_id>", methods=["PUT"])
@jwt_required()
@require_role("doctor")
def update_clinic_by_id(clinic_id):
    """Update clinic by ID. Access: doctor of that clinic."""
    from werkzeug.utils import secure_filename

    current = _current_admin()

    # Check access - doctor can only update their own clinic
    if current.clinic_id != clinic_id:
        return jsonify(
            {"success": False, "error": "Not authorized to update this clinic"}
        ), 403

    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({"success": False, "error": "Clinic not found"}), 404

    # Check if multipart form data (logo upload)
    if request.content_type and "multipart/form-data" in request.content_type:
        name = request.form.get("name")
        address = request.form.get("address")
        phone = request.form.get("phone")
        email = request.form.get("email")
        header_text = request.form.get("header_text")
        footer_text = request.form.get("footer_text")
        remove_logo = request.form.get("remove_logo", "").lower() == "true"
        logo_file = request.files.get("logo")

        if name:
            clinic.name = name
        if address is not None:
            clinic.address = address
        if phone is not None:
            clinic.phone = phone
        if email is not None:
            clinic.email = email
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

        if "name" in data:
            clinic.name = data["name"]
        if "address" in data:
            clinic.address = data["address"]
        if "phone" in data:
            clinic.phone = data["phone"]
        if "email" in data:
            clinic.email = data["email"]
        if "header_text" in data:
            clinic.header_text = data["header_text"]
        if "footer_text" in data:
            clinic.footer_text = data["footer_text"]

    try:
        db.session.commit()

        log_audit(
            "clinic", "update", user_id=current.id, entity_id=str(clinic.id), details={}
        )

        return jsonify(
            {
                "success": True,
                "message": "Clinic updated successfully",
                "data": {
                    "id": clinic.id,
                    "name": clinic.name,
                    "address": clinic.address,
                    "phone": clinic.phone,
                    "email": clinic.email,
                    "license_key": clinic.license_key,
                    "dicom_ae_title": clinic.dicom_ae_title,
                    "is_active": clinic.is_active,
                    "logo_path": clinic.logo_path,
                    "logo_url": f"/api/clinics/{clinic.id}/logo"
                    if clinic.logo_path
                    else None,
                    "header_text": clinic.header_text,
                    "footer_text": clinic.footer_text,
                },
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"success": False, "error": f"Failed to update clinic: {str(e)}"}
        ), 500


@clinic_bp.route("", methods=["GET"])
@jwt_required()
def get_current_clinic():
    """
    Get current user's clinic details with doctor info.
    Access: authenticated user.
    """
    current = _current_admin()
    if not current.clinic_id:
        return jsonify(
            {"success": False, "error": "User is not associated with a clinic"}
        ), 400

    clinic = Clinic.query.get(current.clinic_id)
    if not clinic:
        return jsonify({"success": False, "error": "Clinic not found"}), 404

    # Get doctors for this clinic
    doctors = Admin.query.filter_by(clinic_id=clinic.id, role="doctor").all()

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
    if clinic.logo_path:
        logo_url = f"/api/clinic/logo"

    return jsonify(
        {
            "success": True,
            "data": {
                "id": clinic.id,
                "name": clinic.name,
                "address": clinic.address,
                "phone": clinic.phone,
                "email": clinic.email,
                "license_key": clinic.license_key,
                "dicom_ae_title": clinic.dicom_ae_title,
                "is_active": clinic.is_active,
                "logo_path": clinic.logo_path,
                "logo_url": logo_url,
                "header_text": clinic.header_text,
                "footer_text": clinic.footer_text,
                "doctor": doctor_info,
            },
        }
    ), 200


@clinic_bp.route("", methods=["PUT"])
@jwt_required()
@require_role("doctor")
def update_current_clinic():
    """
    Update current user's clinic details.
    Access: doctor only.

    Supports both JSON and multipart form data.
    Multipart (for logo upload):
        - logo: Image file (jpg, png, svg, webp)
        - name: Clinic name
        - address: Clinic address
        - phone: Contact number
        - email: Email address
        - header_text: PDF header text
        - footer_text: PDF footer text
        - remove_logo: "true" to remove logo
    """
    import os
    from werkzeug.utils import secure_filename

    current = _current_admin()
    if not current.clinic_id:
        return jsonify(
            {"success": False, "error": "User is not associated with a clinic"}
        ), 400

    clinic = Clinic.query.get(current.clinic_id)
    if not clinic:
        return jsonify({"success": False, "error": "Clinic not found"}), 404

    # Check if multipart form data (logo upload)
    if request.content_type and "multipart/form-data" in request.content_type:
        # Handle multipart form data
        name = request.form.get("name")
        address = request.form.get("address")
        phone = request.form.get("phone")
        email = request.form.get("email")
        header_text = request.form.get("header_text")
        footer_text = request.form.get("footer_text")
        remove_logo = request.form.get("remove_logo", "").lower() == "true"
        logo_file = request.files.get("logo")

        if name:
            clinic.name = name
        if address is not None:
            clinic.address = address
        if phone is not None:
            clinic.phone = phone
        if email is not None:
            clinic.email = email
        if header_text is not None:
            clinic.header_text = header_text
        if footer_text is not None:
            clinic.footer_text = footer_text

        # Handle logo
        updated_fields = []
        if remove_logo and clinic.logo_path:
            old_path = os.path.join(
                current_app.config.get("PROJECT_ROOT", ""), clinic.logo_path
            )
            if os.path.exists(old_path):
                os.remove(old_path)
            clinic.logo_path = None
            updated_fields.append("logo_removed")

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
            updated_fields.append("logo")

        data = {k: v for k, v in request.form.items() if v}
        if updated_fields:
            data["updated_files"] = updated_fields
    else:
        # Handle JSON
        data = request.get_json() or {}

        if "name" in data:
            clinic.name = data["name"]
        if "address" in data:
            clinic.address = data["address"]
        if "phone" in data:
            clinic.phone = data["phone"]
        if "email" in data:
            clinic.email = data["email"]
        if "header_text" in data:
            clinic.header_text = data["header_text"]
        if "footer_text" in data:
            clinic.footer_text = data["footer_text"]

    try:
        db.session.commit()

        log_audit(
            "clinic",
            "update",
            user_id=current.id,
            entity_id=str(clinic.id),
            details={"updated_fields": list(data.keys())},
        )

        return jsonify(
            {
                "success": True,
                "message": "Clinic updated successfully",
                "data": {
                    "id": clinic.id,
                    "name": clinic.name,
                    "address": clinic.address,
                    "phone": clinic.phone,
                    "email": clinic.email,
                    "license_key": clinic.license_key,
                    "dicom_ae_title": clinic.dicom_ae_title,
                    "is_active": clinic.is_active,
                    "logo_path": clinic.logo_path,
                    "logo_url": f"/api/clinic/logo" if clinic.logo_path else None,
                    "header_text": clinic.header_text,
                    "footer_text": clinic.footer_text,
                },
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"success": False, "error": f"Failed to update clinic: {str(e)}"}
        ), 500


@clinic_bp.route("/logo", methods=["GET"])
@jwt_required()
def get_clinic_logo():
    """
    Get current clinic's logo.
    Access: authenticated user.
    """
    current = _current_admin()
    if not current.clinic_id:
        return jsonify(
            {"success": False, "error": "User is not associated with a clinic"}
        ), 400

    clinic = Clinic.query.get(current.clinic_id)
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

from flask import Blueprint, request, jsonify
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


@clinic_bp.route("/logo", methods=["POST"])
@jwt_required()
@require_role("doctor")
def upload_clinic_logo():
    """
    Upload logo for the current user's clinic.
    Access: doctor only.

    Multipart form data:
        logo: Image file (jpg, png, svg, webp)
    """
    import os
    from werkzeug.utils import secure_filename
    from flask import current_app

    current = _current_admin()
    if not current.clinic_id:
        return jsonify(
            {"success": False, "error": "User is not associated with a clinic"}
        ), 400

    clinic = Clinic.query.get(current.clinic_id)
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

    filename = f"clinic_{clinic.id}_logo{ext}"
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
            entity_id=str(clinic.id),
            details={"filename": filename},
        )

        return jsonify(
            {
                "success": True,
                "message": "Logo uploaded successfully",
                "data": {
                    "clinic_id": clinic.id,
                    "logo_path": relative_path,
                },
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"success": False, "error": f"Failed to upload logo: {str(e)}"}
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


@clinic_bp.route("/logo", methods=["DELETE"])
@jwt_required()
@require_role("doctor")
def delete_clinic_logo():
    """
    Delete current clinic's logo.
    Access: doctor only.
    """
    import os
    from flask import current_app

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
            entity_id=str(clinic.id),
            details={},
        )

        return jsonify({"success": True, "message": "Logo deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"success": False, "error": f"Failed to delete logo: {str(e)}"}
        ), 500


@clinic_bp.route("", methods=["GET"])
@jwt_required()
def get_current_clinic():
    """
    Get current user's clinic details.
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
                "has_logo": bool(clinic.logo_path),
            },
        }
    ), 200

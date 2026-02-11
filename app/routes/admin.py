from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Admin, Clinic
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
    role = "doctor" if request.blueprint == "admin" else "receptionist"
    query = Admin.query.filter_by(role=role, is_super_admin=False)
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

    user = Admin(
        username=data.get("username"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        email=data.get("email"),
        phone=data.get("phone"),
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

    base_url = Config.PUBLIC_BASE_URL or "http://localhost:8080"
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
                }
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


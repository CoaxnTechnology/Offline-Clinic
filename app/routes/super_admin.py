"""
Super Admin routes (minimal stub to restore missing module).

This provides basic endpoints so the app can start and deployments succeed.
You can extend these later with full multi‑clinic management as needed.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import Admin, Clinic


super_admin_bp = Blueprint("super_admin", __name__, url_prefix="/api/super-admin")


def _current_admin() -> Admin | None:
    try:
        user_id = int(get_jwt_identity())
    except Exception:
        return None
    return Admin.query.get(user_id)


def _require_super_admin(admin: Admin | None):
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


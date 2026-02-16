from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt
from app.models import Admin


def get_current_clinic_id():
    """Returns (clinic_id, is_super_admin) from JWT claims."""
    claims = get_jwt()
    is_super = claims.get("is_super_admin", False)
    if is_super:
        return None, True
    return claims.get("clinic_id"), False


def verify_clinic_access(record, clinic_id, is_super):
    """Returns None if OK, or (jsonify, 404) if record doesn't belong to clinic."""
    if is_super or not hasattr(record, 'clinic_id'):
        return None
    if record.clinic_id != clinic_id:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return None


def require_role(*roles):
    """
    Decorator to require specific roles
    Usage: @require_role('doctor', 'receptionist')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            """
            Require that the current JWT-authenticated user has one of the given roles.
            Must be used together with @jwt_required() on the route.
            """
            try:
                user_id = int(get_jwt_identity())
                user = Admin.query.get(user_id)
            except Exception:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401

            if not user or not user.is_active:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401

            if user.role not in roles:
                return jsonify({
                    'success': False,
                    'error': f'Permission denied. Required roles: {", ".join(roles)}'
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

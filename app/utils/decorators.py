from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt
from app.models import Admin

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

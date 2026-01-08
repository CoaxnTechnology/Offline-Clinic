from functools import wraps
from flask import jsonify
from flask_login import current_user

def require_role(*roles):
    """
    Decorator to require specific roles
    Usage: @require_role('doctor', 'receptionist')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401
            
            if current_user.role not in roles:
                return jsonify({
                    'success': False,
                    'error': f'Permission denied. Required roles: {", ".join(roles)}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

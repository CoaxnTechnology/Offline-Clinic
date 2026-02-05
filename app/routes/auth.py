from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from app.models import Admin
from app.extensions import db
from datetime import datetime, timedelta   # if not already imported

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login endpoint - authenticates admin and returns JWT tokens"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'Username and password required'
        }), 400
    
    admin = Admin.query.filter_by(username=username).first()
    
    if not admin or not admin.check_password(password):
        return jsonify({
            'success': False,
            'error': 'Invalid username or password'
        }), 401
    
    if not admin.is_active:
        return jsonify({
            'success': False,
            'error': 'Account is deactivated'
        }), 403
    
    # Update login tracking
    admin.last_login = datetime.utcnow()
    admin.login_count = (admin.login_count or 0) + 1
    db.session.commit()
    
    # ── JWT part ──────────────────────────────────────────────────────────────
    # Use user id as identity (must be a string for JWT "sub" claim)
    # and put extra info into additional claims.
    identity = str(admin.id)
    additional_claims = {
        "username": admin.username,
        "role": admin.role,
        "is_super_admin": admin.is_super_admin,
        "clinic_id": admin.clinic_id,
    }
    
    # Create access token (short-lived)
    access_token = create_access_token(
        identity=identity,
        additional_claims=additional_claims,
        fresh=True,                         # marks it as "fresh" login
        expires_delta=timedelta(hours=1)    # optional override
    )
    
    # Optional: refresh token (long-lived, used to get new access tokens)
    refresh_token = create_refresh_token(
        identity=identity,
        additional_claims=additional_claims,
    )
    
    # Response – this is what frontend will receive and store
    return jsonify({
        'success': True,
        'data': {
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'role': admin.role,
            'first_name': admin.first_name,
            'last_name': admin.last_name
        },
        'access_token': access_token,
        'refresh_token': refresh_token,   # remove if you don't want refresh tokens
        'token_type': 'bearer',
        'expires_in': 3600                # seconds – match your expires_delta
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()   # ← change from @login_required
def logout():
    """Logout endpoint - in pure JWT usually client just deletes token
       (server can add token blacklisting if needed)"""
    # For stateless JWT → client deletes token
    # If you want server-side logout → implement token blacklist (advanced)
    return jsonify({
        'success': True,
        'message': 'Logged out successfully (delete tokens on client)'
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()   # ← change from @login_required
def get_current_user():
    """Get current logged-in admin information using JWT"""
    # Get user id from token (stored as string)
    user_id = get_jwt_identity()
    
    # Usually fetch full user from DB (don't store sensitive data in JWT)
    admin = Admin.query.get(int(user_id))
    
    if not admin:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'data': {
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'role': admin.role,
            'first_name': admin.first_name,
            'last_name': admin.last_name,
            'phone': admin.phone,
            'is_active': admin.is_active,
            'last_login': admin.last_login.isoformat() if admin.last_login else None,
            'login_count': admin.login_count
        }
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token"""
    try:
        # Identity is user id (string)
        identity = get_jwt_identity()
        # Reuse custom claims from existing token
        claims = get_jwt()
        additional_claims = {
            "username": claims.get("username"),
            "role": claims.get("role"),
            "is_super_admin": claims.get("is_super_admin"),
            "clinic_id": claims.get("clinic_id"),
        }
        new_access_token = create_access_token(
            identity=identity,
            additional_claims=additional_claims,
            fresh=False  # refreshed tokens are not fresh
        )
        return jsonify({
            'success': True,
            'access_token': new_access_token,
            'token_type': 'bearer',
            'expires_in': 3600
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Could not refresh token'
        }), 401

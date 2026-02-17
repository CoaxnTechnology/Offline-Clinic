from flask import Blueprint, request, jsonify, current_app
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
import secrets

from app.services.email_service import send_password_reset_email

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


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Step 1: Request password reset.
    Body: { "email": "user@example.com" }
    Always returns success (does not leak whether email exists).
    """
    data = request.get_json() or {}
    email = data.get('email')
    if not email:
        return jsonify({
            'success': False,
            'error': 'Field "email" is required'
        }), 400

    admin = Admin.query.filter_by(email=email).first()
    if not admin:
        # Do not reveal existence; pretend email sent
        return jsonify({
            'success': True,
            'message': 'If this email exists, a reset link has been sent.'
        }), 200

    # Generate token valid for 1 hour
    token = secrets.token_urlsafe(32)
    admin.reset_token = token
    admin.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()

    # Build reset link - super admins go to admin panel, others to clinic dashboard
    from app.config import Config
    if admin.is_super_admin:
        base_url = Config.SUPER_ADMIN_BASE_URL
    else:
        base_url = current_app.config.get('FRONTEND_BASE_URL') or Config.FRONTEND_BASE_URL
    reset_link = f"{base_url.rstrip('/')}/reset-password/{token}"

    send_password_reset_email(
        email=admin.email,
        reset_link=reset_link,
        user_name=f"{admin.first_name} {admin.last_name}".strip() or admin.username,
    )

    return jsonify({
        'success': True,
        'message': 'If this email exists, a reset link has been sent.'
    }), 200


@auth_bp.route('/verify-reset-token', methods=['POST'])
def verify_reset_token():
    """
    Step 2 (optional): Verify reset token.
    Body: { "token": "<token_from_email>" }
    """
    data = request.get_json() or {}
    token = data.get('token')
    if not token:
        return jsonify({
            'success': False,
            'error': 'Field "token" is required'
        }), 400

    admin = Admin.query.filter_by(reset_token=token).first()
    if not admin or not admin.reset_token_expiry or admin.reset_token_expiry < datetime.utcnow():
        return jsonify({
            'success': False,
            'error': 'Invalid or expired token'
        }), 400

    return jsonify({
        'success': True,
        'message': 'Token is valid'
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Step 3: Reset password using token.
    Body: { "token": "<token_from_email>", "new_password": "newpassword123" }
    """
    data = request.get_json() or {}
    token = data.get('token')
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({
            'success': False,
            'error': 'Fields "token" and "new_password" are required'
        }), 400

    admin = Admin.query.filter_by(reset_token=token).first()
    if not admin or not admin.reset_token_expiry or admin.reset_token_expiry < datetime.utcnow():
        return jsonify({
            'success': False,
            'error': 'Invalid or expired token'
        }), 400

    # Set new password and clear token
    admin.set_password(new_password)
    admin.reset_token = None
    admin.reset_token_expiry = None
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Password has been reset successfully'
    }), 200


@auth_bp.route('/set-password', methods=['POST'])
def set_password():
    """
    First-time password setup (welcome email).
    Body: { "token": "<token_from_welcome_email>", "password": "mypassword123" }
    """
    data = request.get_json() or {}
    token = data.get('token')
    password = data.get('password')

    if not token or not password:
        return jsonify({
            'success': False,
            'error': 'Fields "token" and "password" are required'
        }), 400

    admin = Admin.query.filter_by(reset_token=token).first()
    if not admin or not admin.reset_token_expiry or admin.reset_token_expiry < datetime.utcnow():
        return jsonify({
            'success': False,
            'error': 'Invalid or expired token'
        }), 400

    admin.set_password(password)
    admin.reset_token = None
    admin.reset_token_expiry = None
    admin.is_active = True
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Password set successfully. You can now log in.'
    }), 200

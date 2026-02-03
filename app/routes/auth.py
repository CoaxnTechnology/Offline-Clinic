from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Admin
from app.extensions import db
from app.services.email_service import send_password_reset_email
from datetime import datetime, timedelta
import secrets
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login endpoint - authenticates admin and creates session"""
    # Step 1: Get data from request
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    username = data.get('username')
    password = data.get('password')
    
    # Step 2: Validate input
    if not username or not password:
        return jsonify({
            'success': False,
            'error': 'Username and password required'
        }), 400
    
    # Step 3: Find admin by username
    admin = Admin.query.filter_by(username=username).first()
    
    # Step 4: Check if admin exists and password is correct
    if not admin or not admin.check_password(password):
        return jsonify({
            'success': False,
            'error': 'Invalid username or password'
        }), 401
    
    # Step 5: Check if account is active
    if not admin.is_active:
        return jsonify({
            'success': False,
            'error': 'Account is deactivated'
        }), 403
    
    # Step 6: Update login tracking
    admin.last_login = datetime.utcnow()
    admin.login_count = (admin.login_count or 0) + 1
    db.session.commit()
    
    # Step 7: Login user (creates session)
    login_user(admin)
    
    # Step 8: Return success response
    return jsonify({
        'success': True,
        'data': {
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'role': admin.role,
            'first_name': admin.first_name,
            'last_name': admin.last_name
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout endpoint - clears session"""
    # Step 1: Logout user (clears session)
    logout_user()
    
    # Step 2: Return success
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current logged-in admin information"""
    # Step 1: current_user is automatically available from Flask-Login
    admin = current_user
    
    # Step 2: Return current user info
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


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Request password reset - sends email with reset link
    Body: { "email": "user@example.com" }
    """
    data = request.get_json()
    
    if not data or not data.get('email'):
        return jsonify({
            'success': False,
            'error': 'Email is required'
        }), 400
    
    email = data.get('email').strip().lower()
    
    # Find user by email
    user = Admin.query.filter_by(email=email).first()
    
    # Always return success to prevent email enumeration
    if not user:
        logger.warning(f"Password reset requested for non-existent email: {email}")
        return jsonify({
            'success': True,
            'message': 'If an account with this email exists, a password reset link has been sent.'
        }), 200
    
    # Check if account is active
    if not user.is_active:
        logger.warning(f"Password reset requested for deactivated account: {email}")
        return jsonify({
            'success': True,
            'message': 'If an account with this email exists, a password reset link has been sent.'
        }), 200
    
    # Generate reset token
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    
    try:
        db.session.commit()
        
        # Create reset link (frontend URL)
        # Change this URL to your frontend reset password page
        reset_link = f"http://129.121.75.225/reset-password?token={token}"
        
        # Send email
        email_sent = send_password_reset_email(
            email=user.email,
            reset_link=reset_link,
            user_name=f"{user.first_name} {user.last_name}"
        )
        
        if email_sent:
            logger.info(f"Password reset email sent to {email}")
        else:
            logger.error(f"Failed to send password reset email to {email}")
        
        return jsonify({
            'success': True,
            'message': 'If an account with this email exists, a password reset link has been sent.'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing forgot password: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to process request'
        }), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Reset password using token from email link
    Body: { "token": "reset_token", "new_password": "newpass123" }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token:
        return jsonify({
            'success': False,
            'error': 'Reset token is required'
        }), 400
    
    if not new_password:
        return jsonify({
            'success': False,
            'error': 'New password is required'
        }), 400
    
    if len(new_password) < 6:
        return jsonify({
            'success': False,
            'error': 'Password must be at least 6 characters long'
        }), 400
    
    # Find user by token
    user = Admin.query.filter_by(reset_token=token).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': 'Invalid or expired reset token'
        }), 400
    
    # Check token expiry
    if user.reset_token_expiry < datetime.utcnow():
        # Clear expired token
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': 'Reset token has expired. Please request a new one.'
        }), 400
    
    # Update password
    try:
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        logger.info(f"Password reset successful for user: {user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Password has been reset successfully. You can now login with your new password.'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting password: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to reset password'
        }), 500


@auth_bp.route('/verify-reset-token', methods=['POST'])
def verify_reset_token():
    """
    Verify if reset token is valid (for frontend validation)
    Body: { "token": "reset_token" }
    """
    data = request.get_json()
    
    if not data or not data.get('token'):
        return jsonify({
            'success': False,
            'error': 'Token is required'
        }), 400
    
    token = data.get('token')
    
    # Find user by token
    user = Admin.query.filter_by(reset_token=token).first()
    
    if not user:
        return jsonify({
            'success': False,
            'valid': False,
            'error': 'Invalid reset token'
        }), 400
    
    # Check token expiry
    if user.reset_token_expiry < datetime.utcnow():
        return jsonify({
            'success': False,
            'valid': False,
            'error': 'Reset token has expired'
        }), 400
    
    return jsonify({
        'success': True,
        'valid': True,
        'message': 'Token is valid',
        'data': {
            'email': user.email,
            'username': user.username,
            'name': f"{user.first_name} {user.last_name}",
            'is_new_user': not user.is_active  # True if first time setup
        }
    }), 200


@auth_bp.route('/set-password', methods=['POST'])
def set_password():
    """
    Set password for new user (first time login via email link)
    This also activates the account
    Body: { "token": "token_from_email", "password": "newpassword" }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    token = data.get('token')
    password = data.get('password')
    
    if not token:
        return jsonify({
            'success': False,
            'error': 'Token is required'
        }), 400
    
    if not password:
        return jsonify({
            'success': False,
            'error': 'Password is required'
        }), 400
    
    if len(password) < 6:
        return jsonify({
            'success': False,
            'error': 'Password must be at least 6 characters long'
        }), 400
    
    # Find user by token
    user = Admin.query.filter_by(reset_token=token).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': 'Invalid or expired token'
        }), 400
    
    # Check token expiry
    if user.reset_token_expiry < datetime.utcnow():
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': 'Token has expired. Please contact administrator for a new link.'
        }), 400
    
    # Set password and activate account
    try:
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        user.is_active = True  # Activate the account
        db.session.commit()
        
        logger.info(f"Password set and account activated for user: {user.email}")
        
        return jsonify({
            'success': True,
            'message': 'Password set successfully. Your account is now active. You can login now.',
            'data': {
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error setting password: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to set password'
        }), 500

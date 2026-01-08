from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Admin
from app.extensions import db
from datetime import datetime

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

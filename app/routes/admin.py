from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Admin, Clinic
from app.extensions import db
from app.utils.decorators import require_role
from app.services.email_service import send_welcome_email
from datetime import datetime, timedelta
import secrets
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/doctors')


def require_super_admin_or_self(admin_id=None, current_user=None):
    """
    Helper function to check if user is super admin or accessing own profile
    """
    if not current_user:
        return False
    if current_user.is_super_admin:
        return True
    if admin_id and current_user.id == admin_id:
        return True
    return False


def can_doctor_manage(target_user, current_user=None):
    """
    Check if current doctor can manage target user (receptionist in same clinic)
    """
    if not current_user:
        return False
    if current_user.is_super_admin:
        return True
    if current_user.role == 'doctor':
        if target_user.role == 'receptionist' and target_user.clinic_id == current_user.clinic_id:
            return True
    if current_user.id == target_user.id:
        return True
    return False


@admin_bp.route('', methods=['GET'])
@jwt_required()
def list_admins():
    # Get current user from JWT
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """
    List admin users
    - Super admin: sees all users
    - Doctor: sees self + receptionists in their clinic
    Query params: role, is_active, page, limit
    """
    # Step 1: Get query parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    filter_role = request.args.get('role', type=str)
    filter_active = request.args.get('is_active', type=str)
    
    # Step 2: Validate pagination
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
    
    # Step 3: Start building query
    query = Admin.query
    
    # Step 4: Filter by clinic for doctor
    if not current_user.is_super_admin:
        if current_user.role == 'doctor':
            from sqlalchemy import or_, and_
            query = query.filter(
                or_(
                    Admin.id == current_user.id,
                    and_(Admin.clinic_id == current_user.clinic_id, Admin.role == 'receptionist')
                )
            )
        else:
            query = query.filter(Admin.id == current_user.id)
    
    # Step 5: Apply filters
    if filter_role:
        query = query.filter(Admin.role == filter_role)
    
    if filter_active:
        is_active_bool = filter_active.lower() == 'true'
        query = query.filter(Admin.is_active == is_active_bool)
    
    # Step 6: Get total count
    total = query.count()
    
    # Step 7: Apply pagination
    admins = query.order_by(Admin.created_at.desc()).paginate(
        page=page,
        per_page=limit,
        error_out=False
    )
    
    # Step 8: Format response
    result = []
    for admin in admins.items:
        result.append({
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'first_name': admin.first_name,
            'last_name': admin.last_name,
            'phone': admin.phone,
            'role': admin.role,
            'is_active': admin.is_active,
            'is_super_admin': admin.is_super_admin,
            'clinic_id': admin.clinic_id,
            'last_login': admin.last_login.isoformat() if admin.last_login else None,
            'login_count': admin.login_count,
            'created_at': admin.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'data': result,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': admins.pages,
            'has_next': admins.has_next,
            'has_prev': admins.has_prev
        }
    }), 200


@admin_bp.route('/<int:admin_id>', methods=['GET'])
@jwt_required()
def get_admin(admin_id):
    # Get current user from JWT
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """
    Get single admin by ID
    - Super admin: can view any user
    - Doctor: can view self + receptionists in their clinic
    """
    # Step 1: Find admin
    admin = Admin.query.get(admin_id)
    
    # Step 2: Check if admin exists
    if not admin:
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404
    
    # Step 3: Check permission
    if not can_doctor_manage(admin, current_user):
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    # Step 4: Return admin data
    return jsonify({
        'success': True,
        'data': {
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'first_name': admin.first_name,
            'last_name': admin.last_name,
            'phone': admin.phone,
            'role': admin.role,
            'is_active': admin.is_active,
            'is_super_admin': admin.is_super_admin,
            'clinic_id': admin.clinic_id,
            'last_login': admin.last_login.isoformat() if admin.last_login else None,
            'login_count': admin.login_count,
            'created_at': admin.created_at.isoformat(),
            'updated_at': admin.updated_at.isoformat()
        }
    }), 200


@admin_bp.route('', methods=['POST'])
@jwt_required()
def create_admin():
    # Get current user from JWT
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """
    Create new admin user
    Access: Super admin can create any role
            Doctor can create receptionist only
    Roles: doctor, technician, receptionist
    """
    # Step 1: Check permissions
    is_super = current_user.is_super_admin
    is_doctor = current_user.role == 'doctor'
    
    if not is_super and not is_doctor:
        return jsonify({
            'success': False,
            'error': 'Permission denied. Only super admin or doctor can create users.'
        }), 403
    
    # Step 2: Get data from request
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    # Step 3: Validate required fields (password not required - will be set via email link)
    required_fields = ['username', 'email', 'first_name', 'last_name', 'role']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'error': f'Field "{field}" is required'
            }), 400
    
    # Step 4: Validate role
    valid_roles = ['doctor', 'technician', 'receptionist']
    if data['role'] not in valid_roles:
        return jsonify({
            'success': False,
            'error': f'Invalid role. Valid roles: {", ".join(valid_roles)}'
        }), 400
    
    # Step 4b: Doctor can only create receptionist
    if not current_user.is_super_admin and current_user.role == 'doctor':
        if data['role'] != 'receptionist':
            return jsonify({
                'success': False,
                'error': 'Doctors can only create receptionist users.'
            }), 403
    
    # Step 5: Check if username already exists
    existing_username = Admin.query.filter_by(username=data['username']).first()
    if existing_username:
        return jsonify({
            'success': False,
            'error': f'Username "{data["username"]}" already exists'
        }), 400
    
    # Step 6: Check if email already exists
    existing_email = Admin.query.filter_by(email=data['email']).first()
    if existing_email:
        return jsonify({
            'success': False,
            'error': f'Email "{data["email"]}" already exists'
        }), 400
    
    # Step 7: Create new admin with reset token (no password yet)
    try:
        # Generate token for setting password
        token = secrets.token_urlsafe(32)
        
        # Assign clinic_id: doctor creates receptionist in same clinic
        clinic_id = None
        if current_user.role == 'doctor' and current_user.clinic_id:
            clinic_id = current_user.clinic_id
        elif current_user.is_super_admin and data.get('clinic_id'):
            clinic_id = data.get('clinic_id')
        
        admin = Admin(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            role=data['role'],
            clinic_id=clinic_id,
            is_active=False,  # Not active until password is set
            is_super_admin=False,
            reset_token=token,
            reset_token_expiry=datetime.utcnow() + timedelta(hours=24)
        )
        # Set a random temporary password (user will set their own via link)
        admin.set_password(secrets.token_urlsafe(16))
        
        db.session.add(admin)
        db.session.commit()
        
        # Step 8: Send welcome email with set password link
        clinic_name = None
        if admin.clinic_id:
            clinic = Clinic.query.get(admin.clinic_id)
            clinic_name = clinic.name if clinic else None
        
        # Create set password link (frontend URL)
        from app.config import Config
        base_url = Config.PUBLIC_BASE_URL or "http://localhost:8080"
        set_password_link = f"{base_url.rstrip('/')}/set-password?token={token}"
        
        email_sent = send_welcome_email(
            email=admin.email,
            username=admin.username,
            role=admin.role,
            set_password_link=set_password_link,
            clinic_name=clinic_name
        )
        
        if email_sent:
            logger.info(f"Welcome email sent to {admin.email}")
        else:
            logger.warning(f"Failed to send welcome email to {admin.email}")
        
        # Step 9: Return created admin
        return jsonify({
            'success': True,
            'data': {
                'id': admin.id,
                'username': admin.username,
                'email': admin.email,
                'first_name': admin.first_name,
                'last_name': admin.last_name,
                'phone': admin.phone,
                'role': admin.role,
                'is_active': admin.is_active,
                'created_at': admin.created_at.isoformat()
            },
            'email_sent': email_sent,
            'message': f'User "{admin.username}" created. ' + ('Password setup link sent via email.' if email_sent else 'Email not configured - provide token manually.'),
            'set_password_token': token if not email_sent else None  # Only return token if email failed
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to create admin: {str(e)}'
        }), 500


@admin_bp.route('/<int:admin_id>', methods=['PUT'])
@jwt_required()
def update_admin(admin_id):
    # Get current user from JWT
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """
    Update admin information
    - Super admin: can update any user
    - Doctor: can update self + receptionists in their clinic
    """
    # Step 1: Find admin
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404
    
    # Step 2: Check permission
    if not can_doctor_manage(admin, current_user):
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    # Step 3: Get update data
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    # Step 4: Update fields
    try:
        # List of updatable fields
        updatable_fields = ['email', 'first_name', 'last_name', 'phone']
        
        # Super admin can also update role and is_active
        if current_user.is_super_admin:
            updatable_fields.extend(['role', 'is_active'])
        # Doctor can update is_active for receptionists
        elif current_user.role == 'doctor' and admin.role == 'receptionist':
            updatable_fields.append('is_active')
        
        for field in updatable_fields:
            if field in data:
                # Validate role if updating
                if field == 'role':
                    valid_roles = ['doctor', 'technician', 'receptionist']
                    if data[field] not in valid_roles:
                        return jsonify({
                            'success': False,
                            'error': f'Invalid role. Valid roles: {", ".join(valid_roles)}'
                        }), 400
                
                # Check for duplicate email
                if field == 'email' and data[field] != admin.email:
                    existing_email = Admin.query.filter_by(email=data[field]).first()
                    if existing_email:
                        return jsonify({
                            'success': False,
                            'error': 'Email already exists'
                        }), 400
                
                setattr(admin, field, data[field])
        
        # Prevent changing is_super_admin via API
        if 'is_super_admin' in data:
            return jsonify({
                'success': False,
                'error': 'Cannot change super admin status via API'
            }), 400
        
        db.session.commit()
        
        # Step 5: Return updated admin
        return jsonify({
            'success': True,
            'data': {
                'id': admin.id,
                'username': admin.username,
                'email': admin.email,
                'first_name': admin.first_name,
                'last_name': admin.last_name,
                'phone': admin.phone,
                'role': admin.role,
                'is_active': admin.is_active,
                'clinic_id': admin.clinic_id,
                'updated_at': admin.updated_at.isoformat()
            },
            'message': 'User updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update user: {str(e)}'
        }), 500


@admin_bp.route('/<int:admin_id>/password', methods=['PUT'])
@jwt_required()
def change_password(admin_id):
    # Get current user from JWT
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """
    Change admin password
    Access: Own profile only (or super admin)
    """
    # Step 1: Find admin
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({
            'success': False,
            'error': 'Admin not found'
        }), 404
    
    # Step 2: Check permission (own profile or super admin)
    if not require_super_admin_or_self(admin_id, current_user):
        return jsonify({
            'success': False,
            'error': 'Permission denied. You can only change your own password.'
        }), 403
    
    # Step 3: Get password data
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    new_password = data.get('new_password')
    if not new_password:
        return jsonify({
            'success': False,
            'error': 'Field "new_password" is required'
        }), 400
    
    # Step 4: Validate password length
    if len(new_password) < 6:
        return jsonify({
            'success': False,
            'error': 'Password must be at least 6 characters long'
        }), 400
    
    # Step 5: If not super admin, require old password
    if not current_user.is_super_admin:
        old_password = data.get('old_password')
        if not old_password:
            return jsonify({
                'success': False,
                'error': 'Field "old_password" is required'
            }), 400
        
        if not admin.check_password(old_password):
            return jsonify({
                'success': False,
                'error': 'Current password is incorrect'
            }), 400
    
    # Step 6: Update password
    try:
        admin.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to change password: {str(e)}'
        }), 500


@admin_bp.route('/<int:admin_id>', methods=['DELETE'])
@jwt_required()
def delete_admin(admin_id):
    # Get current user from JWT
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """
    Deactivate user (soft delete by setting is_active=False)
    - Super admin: can deactivate any user
    - Doctor: can deactivate receptionists in their clinic
    """
    # Step 1: Find admin
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404
    
    # Step 2: Check permission
    if not can_doctor_manage(admin, current_user):
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    # Step 3: Prevent deleting super admin
    if admin.is_super_admin:
        return jsonify({
            'success': False,
            'error': 'Cannot deactivate super admin'
        }), 400
    
    # Step 4: Prevent deleting self
    if admin.id == current_user.id:
        return jsonify({
            'success': False,
            'error': 'Cannot deactivate your own account'
        }), 400
    
    # Step 5: Doctor can only deactivate receptionists
    if current_user.role == 'doctor' and admin.role != 'receptionist':
        return jsonify({
            'success': False,
            'error': 'Doctors can only deactivate receptionists'
        }), 403
    
    # Step 6: Deactivate user
    try:
        admin.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User "{admin.username}" deactivated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to deactivate user: {str(e)}'
        }), 500


@admin_bp.route('/<int:admin_id>/activate', methods=['PUT'])
@jwt_required()
def activate_admin(admin_id):
    # Get current user from JWT
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """
    Activate user (set is_active=True)
    - Super admin: can activate any user
    - Doctor: can activate receptionists in their clinic
    """
    # Step 1: Find admin
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({
            'success': False,
            'error': 'User not found'
        }), 404
    
    # Step 2: Check permission
    if not can_doctor_manage(admin, current_user):
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403
    
    # Step 3: Doctor can only activate receptionists
    if current_user.role == 'doctor' and admin.role != 'receptionist':
        return jsonify({
            'success': False,
            'error': 'Doctors can only activate receptionists'
        }), 403
    
    # Step 4: Activate user
    try:
        admin.is_active = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User "{admin.username}" activated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to activate user: {str(e)}'
        }), 500

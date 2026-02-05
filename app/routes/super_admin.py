"""
Super Admin Routes for managing clinics (FREE - No Subscription)
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.models import Clinic, Admin
from app.extensions import db
from app.services.email_service import send_welcome_email
from datetime import datetime, timedelta
import uuid
import hashlib
import secrets
import logging

logger = logging.getLogger(__name__)

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/api/super-admin')


def generate_license_key():
    """Generate unique license key (for identification only)"""
    unique_string = f"{uuid.uuid4()}-{datetime.utcnow().timestamp()}"
    hash_hex = hashlib.sha256(unique_string.encode()).hexdigest()[:16].upper()
    key = '-'.join([hash_hex[i:i+4] for i in range(0, 16, 4)])
    return f"CLINIC-{key}"


def require_super_admin(f):
    """Decorator to require super admin access"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Super admin flag is stored in JWT custom claims
        claims = get_jwt()
        if not claims or not claims.get('is_super_admin'):
            return jsonify({
                'success': False,
                'error': 'Super admin access required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function


# ==================== CLINIC MANAGEMENT ====================

@super_admin_bp.route('/clinics', methods=['GET'])
@jwt_required()
@require_super_admin
def list_clinics():
    """List all clinics"""
    clinics = Clinic.query.all()
    return jsonify({
        'success': True,
        'data': [clinic.to_dict() for clinic in clinics],
        'total': len(clinics)
    }), 200


@super_admin_bp.route('/clinics/<int:clinic_id>', methods=['GET'])
@jwt_required()
@require_super_admin
def get_clinic(clinic_id):
    """Get clinic details"""
    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({'success': False, 'error': 'Clinic not found'}), 404
    
    # Get clinic users
    users = Admin.query.filter_by(clinic_id=clinic_id).all()
    
    return jsonify({
        'success': True,
        'data': {
            **clinic.to_dict(),
            'users': [{
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'is_active': u.is_active
            } for u in users]
        }
    }), 200


@super_admin_bp.route('/clinics', methods=['POST'])
@jwt_required()
@require_super_admin
def create_clinic():
    """Create new clinic (FREE)"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Request body required'}), 400
    
    # Required fields
    if not data.get('name'):
        return jsonify({'success': False, 'error': 'Clinic name is required'}), 400
    
    try:
        clinic = Clinic(
            name=data['name'],
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email'),
            license_key=generate_license_key(),
            max_doctors=1,  # Always 1 doctor per clinic
            is_active=True
        )
        db.session.add(clinic)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Clinic created successfully',
            'data': clinic.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@super_admin_bp.route('/clinics/<int:clinic_id>', methods=['PUT'])
@jwt_required()
@require_super_admin
def update_clinic(clinic_id):
    """Update clinic details"""
    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({'success': False, 'error': 'Clinic not found'}), 404
    
    data = request.get_json()
    
    # Update allowed fields
    if 'name' in data:
        clinic.name = data['name']
    if 'address' in data:
        clinic.address = data['address']
    if 'phone' in data:
        clinic.phone = data['phone']
    if 'email' in data:
        clinic.email = data['email']
    if 'is_active' in data:
        clinic.is_active = data['is_active']
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Clinic updated successfully',
            'data': clinic.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@super_admin_bp.route('/clinics/<int:clinic_id>', methods=['DELETE'])
@jwt_required()
@require_super_admin
def delete_clinic(clinic_id):
    """Deactivate clinic (soft delete)"""
    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({'success': False, 'error': 'Clinic not found'}), 404
    
    clinic.is_active = False
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Clinic deactivated successfully'
    }), 200


@super_admin_bp.route('/clinics/<int:clinic_id>/activate', methods=['POST'])
@jwt_required()
@require_super_admin
def activate_clinic(clinic_id):
    """Activate clinic"""
    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({'success': False, 'error': 'Clinic not found'}), 404
    
    clinic.is_active = True
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Clinic activated successfully'
    }), 200


# ==================== CLINIC USER MANAGEMENT ====================

@super_admin_bp.route('/clinics/<int:clinic_id>/users', methods=['POST'])
@jwt_required()
@require_super_admin
def create_clinic_user(clinic_id):
    """Create user for specific clinic (1 doctor limit)"""
    clinic = Clinic.query.get(clinic_id)
    if not clinic:
        return jsonify({'success': False, 'error': 'Clinic not found'}), 404
    
    if not clinic.is_active:
        return jsonify({'success': False, 'error': 'Clinic is not active'}), 403
    
    data = request.get_json()
    
    # Validate required fields (password not required - will be set via email link)
    required = ['username', 'email', 'first_name', 'last_name', 'role']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required'}), 400
    
    # Validate role
    if data['role'] not in ['doctor', 'receptionist']:
        return jsonify({'success': False, 'error': 'Role must be doctor or receptionist'}), 400
    
    # Check doctor limit (1 per clinic)
    if data['role'] == 'doctor' and not clinic.can_add_doctor():
        return jsonify({
            'success': False, 
            'error': 'Clinic already has a doctor. Only 1 doctor allowed per clinic.'
        }), 403
    
    # Check if username/email exists
    if Admin.query.filter_by(username=data['username']).first():
        return jsonify({'success': False, 'error': 'Username already exists'}), 400
    if Admin.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'error': 'Email already exists'}), 400
    
    try:
        # Generate token for setting password
        token = secrets.token_urlsafe(32)
        
        user = Admin(
            clinic_id=clinic_id,
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            role=data['role'],
            is_active=False,  # Not active until password is set
            is_super_admin=False,
            reset_token=token,
            reset_token_expiry=datetime.utcnow() + timedelta(hours=24)
        )
        # Set a random temporary password
        user.set_password(secrets.token_urlsafe(16))
        
        db.session.add(user)
        db.session.commit()
        
        # Create set password link
        set_password_link = f"http://129.121.75.225/set-password?token={token}"
        
        # Send welcome email with set password link
        email_sent = send_welcome_email(
            email=user.email,
            username=user.username,
            role=user.role,
            set_password_link=set_password_link,
            clinic_name=clinic.name
        )
        
        if email_sent:
            logger.info(f"Welcome email sent to {user.email}")
        else:
            logger.warning(f"Failed to send welcome email to {user.email}")
        
        return jsonify({
            'success': True,
            'message': 'User created. ' + ('Password setup link sent via email.' if email_sent else 'Email not configured.'),
            'data': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'clinic_id': clinic_id,
                'clinic_name': clinic.name,
                'is_active': user.is_active
            },
            'email_sent': email_sent,
            'set_password_token': token if not email_sent else None
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== DASHBOARD / STATS ====================

@super_admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@require_super_admin
def dashboard():
    """Get super admin dashboard stats"""
    from app.models import Patient, Appointment, DicomImage, Report
    
    total_clinics = Clinic.query.count()
    active_clinics = Clinic.query.filter_by(is_active=True).count()
    inactive_clinics = total_clinics - active_clinics
    
    total_users = Admin.query.filter_by(is_super_admin=False).count()
    total_doctors = Admin.query.filter_by(role='doctor', is_super_admin=False).count()
    total_receptionists = Admin.query.filter_by(role='receptionist').count()
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count()
    total_images = DicomImage.query.count()
    total_reports = Report.query.count()
    
    return jsonify({
        'success': True,
        'data': {
            'clinics': {
                'total': total_clinics,
                'active': active_clinics,
                'inactive': inactive_clinics
            },
            'users': {
                'total': total_users,
                'doctors': total_doctors,
                'receptionists': total_receptionists
            },
            'patients': total_patients,
            'appointments': total_appointments,
            'images': total_images,
            'reports': total_reports
        }
    }), 200

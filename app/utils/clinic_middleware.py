"""
Clinic Middleware for Multi-Tenant Support (FREE - No Subscription)
Checks if clinic is active and filters data by clinic_id
"""
from functools import wraps
from flask import jsonify, g
from flask_login import current_user
from app.models import Clinic


def check_clinic_active(f):
    """
    Decorator to check if user's clinic is active
    Skips check for super admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Super admin bypasses all checks
        if current_user.is_super_admin:
            return f(*args, **kwargs)
        
        # Check if user has clinic
        if not current_user.clinic_id:
            return jsonify({
                'success': False,
                'error': 'User is not assigned to any clinic'
            }), 403
        
        # Get clinic
        clinic = Clinic.query.get(current_user.clinic_id)
        if not clinic:
            return jsonify({
                'success': False,
                'error': 'Clinic not found'
            }), 404
        
        # Check if clinic is active
        if not clinic.is_active:
            return jsonify({
                'success': False,
                'error': 'Clinic is deactivated. Contact administrator.'
            }), 403
        
        # Store clinic in g for use in route
        g.clinic = clinic
        g.clinic_id = clinic.id
        
        return f(*args, **kwargs)
    return decorated_function


def get_current_clinic_id():
    """Get current user's clinic_id (or None for super admin)"""
    if not current_user.is_authenticated:
        return None
    if current_user.is_super_admin:
        return None  # Super admin sees all
    return current_user.clinic_id


def filter_by_clinic(query, model):
    """
    Filter query by current user's clinic_id
    Super admin sees all data
    """
    clinic_id = get_current_clinic_id()
    if clinic_id is not None:
        return query.filter(model.clinic_id == clinic_id)
    return query

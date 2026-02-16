"""
Visit API Routes
Manages Visit/Order model (PDF spec: One Visit = One Study = One Report)
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Visit, Appointment, Patient, Admin
from app.utils.decorators import require_role, get_current_clinic_id, verify_clinic_access
from app.utils.audit import log_audit
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

visit_bp = Blueprint('visit', __name__, url_prefix='/api/visits')


@visit_bp.route('', methods=['GET'])
@jwt_required()
def list_visits():
    """
    List visits with pagination and filters
    
    Query params:
        patient_id: Filter by patient ID
        appointment_id: Filter by appointment ID
        visit_status: Filter by visit status
        date: Filter by visit date (YYYY-MM-DD)
        page: Page number (default: 1)
        limit: Items per page (default: 20)
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        patient_id = request.args.get('patient_id')
        appointment_id = request.args.get('appointment_id', type=int)
        visit_status = request.args.get('visit_status')
        date_str = request.args.get('date')
        
        clinic_id, is_super = get_current_clinic_id()
        query = Visit.query.filter_by(deleted_at=None)
        if not is_super and clinic_id:
            query = query.filter(Visit.clinic_id == clinic_id)

        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        if appointment_id:
            query = query.filter_by(appointment_id=appointment_id)
        if visit_status:
            query = query.filter_by(visit_status=visit_status)
        if date_str:
            try:
                visit_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                query = query.filter_by(visit_date=visit_date)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        query = query.order_by(Visit.created_at.desc())
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        
        return jsonify({
            'success': True,
            'data': {
                'visits': [visit.to_dict() for visit in pagination.items],
                'pagination': {
                    'page': pagination.page,
                    'limit': limit,
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        })
    
    except Exception as e:
        logger.error(f"Error listing visits: {e}", exc_info=True)
        error_msg = 'Failed to list visits' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@visit_bp.route('/<int:visit_id>', methods=['GET'])
@jwt_required()
def get_visit(visit_id):
    """Get visit details by ID"""
    try:
        visit = Visit.query.filter_by(id=visit_id, deleted_at=None).first()
        if not visit:
            return jsonify({
                'success': False,
                'error': 'Visit not found'
            }), 404

        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()
        denied = verify_clinic_access(visit, clinic_id, is_super)
        if denied:
            return denied

        return jsonify({
            'success': True,
            'data': visit.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error getting visit {visit_id}: {e}", exc_info=True)
        error_msg = 'Failed to get visit' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@visit_bp.route('/<int:visit_id>', methods=['PUT'])
@jwt_required()
@require_role('receptionist', 'doctor')
def update_visit(visit_id):
    """
    Update visit information
    Access: receptionist, doctor
    """
    try:
        user_id = int(get_jwt_identity())
        visit = Visit.query.filter_by(id=visit_id, deleted_at=None).first()
        if not visit:
            return jsonify({
                'success': False,
                'error': 'Visit not found'
            }), 404

        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()
        denied = verify_clinic_access(visit, clinic_id, is_super)
        if denied:
            return denied

        data = request.get_json() or {}
        
        # Update allowed fields
        if 'visit_status' in data:
            valid_statuses = ['scheduled', 'in_progress', 'completed', 'cancelled']
            if data['visit_status'] not in valid_statuses:
                return jsonify({
                    'success': False,
                    'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
                }), 400
            visit.visit_status = data['visit_status']
        
        if 'exam_type' in data:
            visit.exam_type = data['exam_type']
        
        if 'modality' in data:
            visit.modality = data['modality']
        
        if 'study_instance_uid' in data:
            visit.study_instance_uid = data['study_instance_uid']
        
        db.session.commit()
        log_audit('visit', 'update', user_id=user_id, entity_id=str(visit_id), details={'status': visit.visit_status})
        
        return jsonify({
            'success': True,
            'message': 'Visit updated successfully',
            'data': visit.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error updating visit {visit_id}: {e}", exc_info=True)
        db.session.rollback()
        error_msg = 'Failed to update visit' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

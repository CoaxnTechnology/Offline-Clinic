from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import Patient, Appointment
from app.extensions import db
from app.utils.decorators import require_role
from sqlalchemy import or_
from datetime import datetime

patient_bp = Blueprint('patient', __name__, url_prefix='/api/patients')


def parse_date(date_string):
    """Parse date string to date object"""
    if not date_string:
        return None
    try:
        return datetime.fromisoformat(date_string).date()
    except:
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except:
            return None


@patient_bp.route('', methods=['GET'])
@login_required
def list_patients():
    """
    List all patients with pagination and search
    Query params: page, limit, search
    """
    # Step 1: Get query parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search', '', type=str).strip()
    
    # Step 2: Validate pagination
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
    
    # Step 3: Start building query
    query = Patient.query
    
    # Step 4: Apply search filter if provided
    if search:
        search_filter = or_(
            Patient.first_name.ilike(f'%{search}%'),
            Patient.last_name.ilike(f'%{search}%'),
            Patient.phone.ilike(f'%{search}%'),
            Patient.email.ilike(f'%{search}%'),
            Patient.id.ilike(f'%{search}%')
        )
        query = query.filter(search_filter)
    
    # Step 5: Get total count (before pagination)
    total = query.count()
    
    # Step 6: Apply pagination
    patients = query.order_by(Patient.created_at.desc()).paginate(
        page=page,
        per_page=limit,
        error_out=False
    )
    
    # Step 7: Format response
    return jsonify({
        'success': True,
        'data': [{
            'id': p.id,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'phone': p.phone,
            'email': p.email,
            'gender': p.gender,
            'birth_date': p.birth_date.isoformat() if p.birth_date else None,
            'created_at': p.created_at.isoformat()
        } for p in patients.items],
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': patients.pages,
            'has_next': patients.has_next,
            'has_prev': patients.has_prev
        }
    }), 200


@patient_bp.route('/<patient_id>', methods=['GET'])
@login_required
def get_patient(patient_id):
    """
    Get single patient by ID
    """
    # Step 1: Find patient by ID
    patient = Patient.query.filter_by(id=patient_id).first()
    
    # Step 2: Check if patient exists
    if not patient:
        return jsonify({
            'success': False,
            'error': 'Patient not found'
        }), 404
    
    # Step 3: Return patient data
    return jsonify({
        'success': True,
        'data': {
            'id': patient.id,
            'title': patient.title,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'gender': patient.gender,
            'birth_date': patient.birth_date.isoformat() if patient.birth_date else None,
            'phone': patient.phone,
            'email': patient.email,
            'identity_number': patient.identity_number,
            'height': patient.height,
            'weight': patient.weight,
            'blood_group': patient.blood_group,
            'notes': patient.notes,
            'primary_doctor': patient.primary_doctor,
            'new_patient': patient.new_patient,
            'demographics': patient.demographics,
            'created_at': patient.created_at.isoformat(),
            'updated_at': patient.updated_at.isoformat()
        }
    }), 200


@patient_bp.route('', methods=['POST'])
@login_required
@require_role('receptionist', 'doctor')
def create_patient():
    """
    Create new patient
    Access: receptionist, doctor
    """
    # Step 1: Get data from request
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    # Step 2: Validate required fields
    required_fields = ['id', 'first_name', 'last_name', 'phone']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'error': f'Field "{field}" is required'
            }), 400
    
    # Step 3: Check if patient ID already exists
    existing = Patient.query.filter_by(id=data['id']).first()
    if existing:
        return jsonify({
            'success': False,
            'error': f'Patient with ID {data["id"]} already exists'
        }), 400
    
    # Step 4: Check if phone already exists
    if data.get('phone'):
        existing_phone = Patient.query.filter_by(phone=data['phone']).first()
        if existing_phone:
            return jsonify({
                'success': False,
                'error': 'Phone number already exists'
            }), 400
    
    # Step 5: Check if email already exists (if provided)
    if data.get('email'):
        existing_email = Patient.query.filter_by(email=data['email']).first()
        if existing_email:
            return jsonify({
                'success': False,
                'error': 'Email already exists'
            }), 400
    
    # Step 6: Create new patient
    try:
        patient = Patient(
            id=data['id'],
            title=data.get('title'),
            first_name=data['first_name'],
            last_name=data['last_name'],
            gender=data.get('gender'),
            birth_date=parse_date(data.get('birth_date')),
            phone=data['phone'],
            email=data.get('email'),
            identity_number=data.get('identity_number'),
            height=data.get('height'),
            weight=data.get('weight'),
            blood_group=data.get('blood_group'),
            notes=data.get('notes'),
            primary_doctor=data.get('primary_doctor'),
            new_patient=data.get('new_patient', True),
            demographics=data.get('demographics')
        )
        
        db.session.add(patient)
        db.session.commit()
        
        # Step 7: Return created patient
        return jsonify({
            'success': True,
            'data': {
                'id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'phone': patient.phone,
                'email': patient.email,
                'gender': patient.gender,
                'birth_date': patient.birth_date.isoformat() if patient.birth_date else None,
                'created_at': patient.created_at.isoformat()
            },
            'message': 'Patient created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to create patient: {str(e)}'
        }), 500


@patient_bp.route('/<patient_id>', methods=['PUT'])
@login_required
@require_role('receptionist', 'doctor')
def update_patient(patient_id):
    """
    Update patient information
    Access: receptionist, doctor
    """
    # Step 1: Find patient
    patient = Patient.query.filter_by(id=patient_id).first()
    if not patient:
        return jsonify({
            'success': False,
            'error': 'Patient not found'
        }), 404
    
    # Step 2: Get update data
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    # Step 3: Update fields (only provided fields)
    try:
        # Check for duplicate phone if phone is being updated
        if 'phone' in data and data['phone'] != patient.phone:
            existing_phone = Patient.query.filter_by(phone=data['phone']).first()
            if existing_phone:
                return jsonify({
                    'success': False,
                    'error': 'Phone number already exists'
                }), 400
        
        # Check for duplicate email if email is being updated
        if 'email' in data and data['email'] != patient.email:
            existing_email = Patient.query.filter_by(email=data['email']).first()
            if existing_email:
                return jsonify({
                    'success': False,
                    'error': 'Email already exists'
                }), 400
        
        # List of updatable fields
        updatable_fields = [
            'title', 'first_name', 'last_name', 'gender',
            'birth_date', 'phone', 'email', 'identity_number', 'height',
            'weight', 'blood_group', 'notes', 'primary_doctor',
            'new_patient', 'demographics'
        ]
        
        for field in updatable_fields:
            if field in data:
                # Special handling for date fields
                if field == 'birth_date':
                    setattr(patient, field, parse_date(data[field]))
                else:
                    setattr(patient, field, data[field])
        
        # Update timestamp is automatic (TimestampMixin handles it)
        db.session.commit()
        
        # Step 4: Return updated patient
        return jsonify({
            'success': True,
            'data': {
                'id': patient.id,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'phone': patient.phone,
                'email': patient.email,
                'gender': patient.gender,
                'birth_date': patient.birth_date.isoformat() if patient.birth_date else None,
                'updated_at': patient.updated_at.isoformat()
            },
            'message': 'Patient updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update patient: {str(e)}'
        }), 500


@patient_bp.route('/<patient_id>', methods=['DELETE'])
@login_required
@require_role('receptionist', 'doctor')
def delete_patient(patient_id):
    """
    Delete patient
    Access: receptionist, doctor
    Note: This is hard delete. Checks for appointments before deletion.
    """
    # Step 1: Find patient
    patient = Patient.query.filter_by(id=patient_id).first()
    if not patient:
        return jsonify({
            'success': False,
            'error': 'Patient not found'
        }), 404
    
    # Step 2: Check if patient has appointments
    appointments_count = Appointment.query.filter_by(patient_id=patient_id).count()
    if appointments_count > 0:
        return jsonify({
            'success': False,
            'error': f'Cannot delete patient. Patient has {appointments_count} appointment(s).'
        }), 400
    
    # Step 3: Delete patient
    try:
        db.session.delete(patient)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Patient {patient_id} deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete patient: {str(e)}'
        }), 500


@patient_bp.route('/search', methods=['GET'])
@login_required
def search_patients():
    """
    Search patients by name, phone, or ID
    Query param: q (search query)
    """
    # Step 1: Get search query
    query = request.args.get('q', '', type=str).strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Search query "q" parameter is required'
        }), 400
    
    # Step 2: Build search query
    search_filter = or_(
        Patient.first_name.ilike(f'%{query}%'),
        Patient.last_name.ilike(f'%{query}%'),
        Patient.phone.ilike(f'%{query}%'),
        Patient.email.ilike(f'%{query}%'),
        Patient.id.ilike(f'%{query}%')
    )
    
    # Step 3: Execute search
    patients = Patient.query.filter(search_filter).limit(50).all()
    
    # Step 4: Format response
    return jsonify({
        'success': True,
        'data': [{
            'id': p.id,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'phone': p.phone,
            'email': p.email,
            'gender': p.gender,
            'birth_date': p.birth_date.isoformat() if p.birth_date else None
        } for p in patients],
        'count': len(patients)
    }), 200

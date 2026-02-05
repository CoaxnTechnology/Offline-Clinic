from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
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
@jwt_required()
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
    
    # Step 7: Format response (FULL patient info per item)
    return jsonify({
        'success': True,
        'data': [{
            'id': p.id,
            'title': p.title,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'maiden_name': p.maiden_name,
            'gender': p.gender,
            'birth_date': p.birth_date.isoformat() if p.birth_date else None,
            'phone': p.phone,
            'secondary_phone': p.secondary_phone,
            'other_phone': p.other_phone,
            'email': p.email,
            'identity_number': p.identity_number,
            'social_security_number': p.social_security_number,
            'occupation': p.occupation,
            'height': p.height,
            'weight': p.weight,
            'blood_group': p.blood_group,
            'smoker': p.smoker,
            'cigarettes_per_day': p.cigarettes_per_day,
            'family_history': p.family_history,
            'medical_history': p.medical_history,
            'gynecological_history': p.gynecological_history,
            'allergies': p.allergies,
            'notes': p.notes,
            'primary_doctor': p.primary_doctor,
            'delivery_location': p.delivery_location,
            'legacy_number': p.legacy_number,
            'new_patient': p.new_patient,
            'created_at': p.created_at.isoformat(),
            'updated_at': p.updated_at.isoformat() if p.updated_at else None
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
@jwt_required()
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
            'maiden_name': patient.maiden_name,
            'gender': patient.gender,
            'birth_date': patient.birth_date.isoformat() if patient.birth_date else None,
            'phone': patient.phone,
            'secondary_phone': patient.secondary_phone,
            'other_phone': patient.other_phone,
            'email': patient.email,
            'identity_number': patient.identity_number,
            'social_security_number': patient.social_security_number,
            'occupation': patient.occupation,
            'height': patient.height,
            'weight': patient.weight,
            'blood_group': patient.blood_group,
            'smoker': patient.smoker,
            'cigarettes_per_day': patient.cigarettes_per_day,
            'family_history': patient.family_history,
            'medical_history': patient.medical_history,
            'gynecological_history': patient.gynecological_history,
            'allergies': patient.allergies,
            'notes': patient.notes,
            'primary_doctor': patient.primary_doctor,
            'delivery_location': patient.delivery_location,
            'legacy_number': patient.legacy_number,
            'new_patient': patient.new_patient,
            'created_at': patient.created_at.isoformat(),
            'updated_at': patient.updated_at.isoformat()
        }
    }), 200


@patient_bp.route('', methods=['POST'])
@jwt_required()
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

    # Helper to normalize string fields: if missing/empty -> "N/A"
    def norm_str(field_name, default="N/A"):
        value = data.get(field_name)
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return value

    # Helper to normalize numeric fields: if missing/empty -> 0
    def norm_num(field_name):
        value = data.get(field_name)
        if value in (None, "", " "):
            return 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0
    
    # Step 2: Validate required fields
    # ID is now generated by backend; client should not send it
    required_fields = ['first_name', 'last_name', 'phone']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'error': f'Field "{field}" is required'
            }), 400
    
    # Step 3: Check if phone already exists
    if data.get('phone'):
        existing_phone = Patient.query.filter_by(phone=data['phone']).first()
        if existing_phone:
            return jsonify({
                'success': False,
                'error': 'Phone number already exists'
            }), 400
    
    # Step 4: Check if email already exists (if provided)
    if data.get('email'):
        existing_email = Patient.query.filter_by(email=data['email']).first()
        if existing_email:
            return jsonify({
                'success': False,
                'error': 'Email already exists'
            }), 400
    
    # Step 5: Create new patient (ID generated by backend)
    try:
        # Generate a unique patient ID
        new_id = Patient.generate_new_id()
        # Simple safety check in case of race conditions
        while Patient.query.filter_by(id=new_id).first():
            new_id = Patient.generate_new_id()

        patient = Patient(
            id=new_id,
            title=norm_str('title'),
            first_name=data['first_name'],
            last_name=data['last_name'],
            maiden_name=norm_str('maiden_name'),
            gender=norm_str('gender'),
            birth_date=parse_date(data.get('birth_date')),
            phone=data['phone'],
            secondary_phone=norm_str('secondary_phone'),
            other_phone=norm_str('other_phone'),
            email=norm_str('email'),
            identity_number=norm_str('identity_number'),
            social_security_number=norm_str('social_security_number'),
            occupation=norm_str('occupation'),
            height=norm_num('height'),
            weight=norm_num('weight'),
            blood_group=norm_str('blood_group'),
            smoker=norm_str('smoker'),
            cigarettes_per_day=int(norm_num('cigarettes_per_day')),
            family_history=norm_str('family_history'),
            medical_history=norm_str('medical_history'),
            gynecological_history=norm_str('gynecological_history'),
            allergies=norm_str('allergies'),
            notes=norm_str('notes'),
            primary_doctor=norm_str('primary_doctor'),
            delivery_location=norm_str('delivery_location'),
            legacy_number=norm_str('legacy_number'),
            new_patient=data.get('new_patient', True)
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
@jwt_required()
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
            'title', 'first_name', 'last_name', 'maiden_name', 'gender',
            'birth_date', 'phone', 'secondary_phone', 'other_phone',
            'email', 'identity_number', 'social_security_number',
            'occupation', 'height', 'weight', 'blood_group', 'smoker',
            'cigarettes_per_day', 'family_history', 'medical_history',
            'gynecological_history', 'allergies', 'notes', 'primary_doctor',
            'delivery_location', 'legacy_number', 'new_patient'
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
                'title': patient.title,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'maiden_name': patient.maiden_name,
                'gender': patient.gender,
                'birth_date': patient.birth_date.isoformat() if patient.birth_date else None,
                'phone': patient.phone,
                'secondary_phone': patient.secondary_phone,
                'other_phone': patient.other_phone,
                'email': patient.email,
                'identity_number': patient.identity_number,
                'social_security_number': patient.social_security_number,
                'occupation': patient.occupation,
                'height': patient.height,
                'weight': patient.weight,
                'blood_group': patient.blood_group,
                'smoker': patient.smoker,
                'cigarettes_per_day': patient.cigarettes_per_day,
                'family_history': patient.family_history,
                'medical_history': patient.medical_history,
                'gynecological_history': patient.gynecological_history,
                'allergies': patient.allergies,
                'notes': patient.notes,
                'primary_doctor': patient.primary_doctor,
                'delivery_location': patient.delivery_location,
                'legacy_number': patient.legacy_number,
                'new_patient': patient.new_patient,
                'created_at': patient.created_at.isoformat(),
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
@jwt_required()
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
@jwt_required()
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

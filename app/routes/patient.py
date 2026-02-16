from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Patient, Appointment
from app.models.admin import Admin
from app.extensions import db
from app.utils.decorators import require_role, get_current_clinic_id, verify_clinic_access
from app.utils.audit import log_audit
from sqlalchemy import or_
from datetime import datetime

patient_bp = Blueprint('patient', __name__, url_prefix='/api/patients')


def _empty_to_na(val):
    """Return 'N/A' for None or empty string; otherwise return value."""
    if val is None:
        return "N/A"
    if isinstance(val, str) and not val.strip():
        return "N/A"
    return val


def _patient_to_dict(p):
    """Build patient dict with empty fields as 'N/A'."""
    return {
        'id': p.id,
        'title': _empty_to_na(p.title),
        'first_name': p.first_name or "N/A",
        'last_name': p.last_name or "N/A",
        'maiden_name': _empty_to_na(p.maiden_name),
        'gender': _empty_to_na(p.gender),
        'birth_date': p.birth_date.isoformat() if p.birth_date else "N/A",
        'phone': p.phone or "N/A",
        'secondary_phone': _empty_to_na(p.secondary_phone),
        'other_phone': _empty_to_na(p.other_phone),
        'email': _empty_to_na(p.email),
        'identity_number': _empty_to_na(p.identity_number),
        'social_security_number': _empty_to_na(p.social_security_number),
        'occupation': _empty_to_na(p.occupation),
        'height': _empty_to_na(p.height) if p.height is None else p.height,
        'weight': _empty_to_na(p.weight) if p.weight is None else p.weight,
        'blood_group': _empty_to_na(p.blood_group),
        'smoker': _empty_to_na(p.smoker),
        'cigarettes_per_day': _empty_to_na(p.cigarettes_per_day) if p.cigarettes_per_day is None else p.cigarettes_per_day,
        'family_history': _empty_to_na(p.family_history),
        'medical_history': _empty_to_na(p.medical_history),
        'gynecological_history': _empty_to_na(p.gynecological_history),
        'allergies': _empty_to_na(p.allergies),
        'notes': _empty_to_na(p.notes),
        'primary_doctor': _empty_to_na(p.primary_doctor),
        'delivery_location': _empty_to_na(p.delivery_location),
        'legacy_number': _empty_to_na(p.legacy_number),
        'new_patient': p.new_patient if p.new_patient is not None else True,
        'created_at': p.created_at.isoformat() if p.created_at else "N/A",
        'updated_at': p.updated_at.isoformat() if p.updated_at else "N/A",
    }


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
    
    # Step 3: Start building query (exclude soft-deleted - PDF spec §9)
    clinic_id, is_super = get_current_clinic_id()
    query = Patient.query.filter(Patient.deleted_at.is_(None))
    if not is_super and clinic_id:
        query = query.filter(Patient.clinic_id == clinic_id)

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
    
    # Step 7: Format response (full patient info; empty fields as N/A)
    return jsonify({
        'success': True,
        'data': [_patient_to_dict(p) for p in patients.items],
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
    # Step 1: Find patient by ID (exclude soft-deleted)
    patient = Patient.query.filter_by(id=patient_id).filter(Patient.deleted_at.is_(None)).first()

    # Step 2: Check if patient exists
    if not patient:
        return jsonify({
            'success': False,
            'error': 'Patient not found'
        }), 404

    # Clinic isolation
    clinic_id, is_super = get_current_clinic_id()
    denied = verify_clinic_access(patient, clinic_id, is_super)
    if denied:
        return denied

    # Step 3: Build base patient data (empty fields as N/A)
    data = _patient_to_dict(patient)

    # Step 4: Attach latest prescription id for this patient (if any)
    try:
        from app.models import Prescription

        latest_rx = (
            Prescription.query.filter_by(patient_id=patient_id)
            .order_by(Prescription.created_at.desc())
            .first()
        )
        data["latest_prescription_id"] = latest_rx.id if latest_rx else None
    except Exception:
        # If anything goes wrong, don't break the endpoint
        data["latest_prescription_id"] = None

    return jsonify({
        'success': True,
        'data': data
    }), 200


@patient_bp.route('/<patient_id>/history', methods=['GET'])
@jwt_required()
def get_patient_history(patient_id):
    """
    Get full history for a patient by ID.
    
    Includes:
      - Patient info (full details)
      - DICOM studies/images
      - Prescriptions
      - Appointments
    """
    # Step 1: Find patient (exclude soft-deleted)
    patient = Patient.query.filter_by(id=patient_id).filter(Patient.deleted_at.is_(None)).first()
    if not patient:
        return jsonify({
            'success': False,
            'error': 'Patient not found'
        }), 404

    # Clinic isolation
    clinic_id, is_super = get_current_clinic_id()
    denied = verify_clinic_access(patient, clinic_id, is_super)
    if denied:
        return denied

    # Import related models lazily to avoid circular imports
    from app.models import DicomImage, Prescription, Appointment

    # Step 2: Build patient info
    patient_info = _patient_to_dict(patient)

    # Step 3: DICOM history (all studies/images for this patient)
    dicom_images = (
        DicomImage.query
        .filter(DicomImage.patient_id == patient_id)
        .order_by(DicomImage.study_date.desc(), DicomImage.study_time.desc().nullslast())
        .all()
    )
    dicom_list = [img.to_dict() for img in dicom_images]

    # Step 4: Prescription history
    prescriptions = (
        Prescription.query
        .filter_by(patient_id=patient_id)
        .order_by(Prescription.created_at.desc())
        .all()
    )
    prescriptions_list = [p.to_dict() for p in prescriptions]

    # Step 5: Appointment history (exclude soft-deleted)
    appointments = (
        Appointment.query
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.deleted_at.is_(None)
        )
        .order_by(Appointment.date.desc(), Appointment.time.asc())
        .all()
    )
    appointments_list = []
    for apt in appointments:
        appointments_list.append({
            'id': apt.id,
            'date': apt.date.isoformat() if apt.date else None,
            'time': apt.time,
            'doctor': apt.doctor,
            'status': apt.status,
            'accession_number': apt.accession_number,
            'requested_procedure_id': apt.requested_procedure_id,
            'scheduled_procedure_step_id': apt.scheduled_procedure_step_id,
            'created_at': apt.created_at.isoformat() if apt.created_at else None,
            'updated_at': apt.updated_at.isoformat() if apt.updated_at else None,
        })

    # Step 6: Build per-date timeline combining appointments, prescriptions, and DICOM
    # The key is the calendar date (YYYY-MM-DD). For each date we include:
    #   - all appointments on that date
    #   - all prescriptions created on that date
    #   - all DICOM studies/images with study_date equal to that date
    timeline_by_date = {}

    def _ensure_day(date_str):
        if not date_str:
            return None
        if date_str not in timeline_by_date:
            timeline_by_date[date_str] = {
                'date': date_str,
                'appointments': [],
                'prescriptions': [],
                'dicom': [],
            }
        return timeline_by_date[date_str]

    # Appointments grouped by their appointment date
    for apt in appointments_list:
        day = apt.get('date')
        day_bucket = _ensure_day(day)
        if day_bucket is not None:
            day_bucket['appointments'].append(apt)

    # Prescriptions grouped by created_at date
    for p in prescriptions_list:
        created_at = p.get('created_at')
        day = created_at.split('T')[0] if created_at else None
        day_bucket = _ensure_day(day)
        if day_bucket is not None:
            day_bucket['prescriptions'].append(p)

    # DICOM grouped by study_date
    for img in dicom_list:
        study_date = img.get('study_date')
        day_bucket = _ensure_day(study_date)
        if day_bucket is not None:
            day_bucket['dicom'].append(img)

    # Convert timeline dict to sorted list (newest date first)
    timeline = sorted(
        timeline_by_date.values(),
        key=lambda d: d['date'],
        reverse=True,
    )

    return jsonify({
        'success': True,
        'data': {
            'patient': patient_info,
            'dicom': dicom_list,
            'prescriptions': prescriptions_list,
            'appointments': appointments_list,
            # Combined per-day history: each entry has date, appointments, prescriptions, dicom.
            'timeline': timeline,
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
    
    # Step 5: Get clinic_id from JWT claims
    clinic_id, is_super = get_current_clinic_id()
    if not is_super and not clinic_id:
        return jsonify({
            'success': False,
            'error': 'User is not assigned to a clinic'
        }), 400

    # Step 6: Create new patient (ID generated by backend)
    try:
        # Generate a unique clinic-scoped patient ID
        new_id = Patient.generate_new_id(clinic_id)
        # Simple safety check in case of race conditions
        while Patient.query.filter_by(id=new_id).first():
            new_id = Patient.generate_new_id(clinic_id)

        patient = Patient(
            id=new_id,
            clinic_id=clinic_id,
            title=norm_str('title'),
            first_name=data['first_name'],
            last_name=data['last_name'],
            maiden_name=norm_str('maiden_name'),
            gender=norm_str('gender'),
            birth_date=parse_date(data.get('birth_date')),
            phone=data['phone'],
            secondary_phone=norm_str('secondary_phone'),
            other_phone=norm_str('other_phone'),
            email=norm_str('email', default=None),
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
        
        # Audit log
        user_id = int(get_jwt_identity())
        log_audit('patient', 'create', user_id=user_id, entity_id=patient.id, details={'name': f"{patient.first_name} {patient.last_name}"})
        
        # Step 7: Return created patient (full info; empty fields as N/A)
        return jsonify({
            'success': True,
            'data': _patient_to_dict(patient),
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
    # Step 1: Find patient (exclude soft-deleted)
    patient = Patient.query.filter_by(id=patient_id).filter(Patient.deleted_at.is_(None)).first()
    if not patient:
        return jsonify({
            'success': False,
            'error': 'Patient not found'
        }), 404

    # Clinic isolation
    clinic_id, is_super = get_current_clinic_id()
    denied = verify_clinic_access(patient, clinic_id, is_super)
    if denied:
        return denied

    # Step 2: Get update data
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400

    # Helper to normalize string fields on update: if explicitly set to empty -> "N/A"
    def norm_str_update(field_name, current_value):
        if field_name not in data:
            return current_value
        value = data.get(field_name)
        if value is None:
            return "N/A"
        if isinstance(value, str) and not value.strip():
            return "N/A"
        return value

    # Helper to normalize numeric fields on update: if explicitly empty -> 0
    def norm_num_update(field_name, current_value):
        if field_name not in data:
            return current_value
        value = data.get(field_name)
        if value in (None, "", " "):
            return 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0
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
        
        # Update scalar fields with normalization
        patient.title = norm_str_update('title', patient.title)
        if 'first_name' in data:
            patient.first_name = data['first_name']
        if 'last_name' in data:
            patient.last_name = data['last_name']
        patient.maiden_name = norm_str_update('maiden_name', patient.maiden_name)
        patient.gender = norm_str_update('gender', patient.gender)
        if 'birth_date' in data:
            patient.birth_date = parse_date(data.get('birth_date'))
        if 'phone' in data:
            patient.phone = data['phone']
        patient.secondary_phone = norm_str_update('secondary_phone', patient.secondary_phone)
        patient.other_phone = norm_str_update('other_phone', patient.other_phone)
        patient.email = norm_str_update('email', patient.email)
        patient.identity_number = norm_str_update('identity_number', patient.identity_number)
        patient.social_security_number = norm_str_update('social_security_number', patient.social_security_number)
        patient.occupation = norm_str_update('occupation', patient.occupation)
        patient.height = norm_num_update('height', patient.height)
        patient.weight = norm_num_update('weight', patient.weight)
        patient.blood_group = norm_str_update('blood_group', patient.blood_group)
        patient.smoker = norm_str_update('smoker', patient.smoker)
        patient.cigarettes_per_day = int(norm_num_update('cigarettes_per_day', patient.cigarettes_per_day or 0))
        patient.family_history = norm_str_update('family_history', patient.family_history)
        patient.medical_history = norm_str_update('medical_history', patient.medical_history)
        patient.gynecological_history = norm_str_update('gynecological_history', patient.gynecological_history)
        patient.allergies = norm_str_update('allergies', patient.allergies)
        patient.notes = norm_str_update('notes', patient.notes)
        patient.primary_doctor = norm_str_update('primary_doctor', patient.primary_doctor)
        patient.delivery_location = norm_str_update('delivery_location', patient.delivery_location)
        patient.legacy_number = norm_str_update('legacy_number', patient.legacy_number)
        if 'new_patient' in data:
            patient.new_patient = data.get('new_patient', patient.new_patient)
        
        # Update timestamp is automatic (TimestampMixin handles it)
        db.session.commit()
        
        # Step 4: Return updated patient (empty fields as N/A)
        return jsonify({
            'success': True,
            'data': _patient_to_dict(patient),
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
    Soft-delete patient (PDF spec §9: no hard deletion of medical data).
    Access: receptionist, doctor
    """
    from datetime import datetime as dt
    patient = Patient.query.filter_by(id=patient_id).filter(Patient.deleted_at.is_(None)).first()
    if not patient:
        return jsonify({
            'success': False,
            'error': 'Patient not found'
        }), 404

    # Clinic isolation
    clinic_id, is_super = get_current_clinic_id()
    denied = verify_clinic_access(patient, clinic_id, is_super)
    if denied:
        return denied

    try:
        user_id = int(get_jwt_identity())
        patient.deleted_at = dt.utcnow()
        db.session.commit()
        log_audit('patient', 'delete', user_id=user_id, entity_id=patient_id, details={'name': f"{patient.first_name} {patient.last_name}"})
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
    Search patients by name, phone, email, or ID
    Query param: q (search query)
    """
    # Step 1: Get search query
    query = request.args.get('q', '', type=str).strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Search query "q" parameter is required'
        }), 400
    
    # Step 2: Build search query (case-insensitive, partial match)
    # Search in: first_name, last_name, phone, email, patient ID
    search_filter = or_(
        Patient.first_name.ilike(f'%{query}%'),
        Patient.last_name.ilike(f'%{query}%'),
        Patient.phone.ilike(f'%{query}%'),
        Patient.email.ilike(f'%{query}%'),
        Patient.id.ilike(f'%{query}%')
    )
    
    # Clinic isolation
    clinic_id, is_super = get_current_clinic_id()

    # Step 3: Execute search (exclude soft-deleted only)
    base_query = Patient.query.filter(Patient.deleted_at.is_(None))
    if not is_super and clinic_id:
        base_query = base_query.filter(Patient.clinic_id == clinic_id)
    patients = base_query.filter(search_filter).limit(50).all()
    
    # Step 4: Format response (full patient info; empty fields as N/A)
    return jsonify({
        'success': True,
        'data': [_patient_to_dict(p) for p in patients],
        'count': len(patients),
        'query': query  # Include query for debugging
    }), 200

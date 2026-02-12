from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Appointment, Patient, Admin
from app.extensions import db
from app.utils.decorators import require_role
from app.utils.audit import log_audit
from datetime import datetime, date
from app.routes.patient import _patient_to_dict  # Reuse full patient formatter

appointment_bp = Blueprint('appointment', __name__, url_prefix='/api/appointments')


@appointment_bp.route('', methods=['GET'])
@jwt_required()
def list_appointments():
    """
    List appointments for a given date (default: today) with filters and pagination.
    Query params:
        date: YYYY-MM-DD (optional, defaults to today's date)
        patient_id: Filter by patient ID (optional)
        doctor: Filter by doctor name (optional)
        doctor_id: Filter by doctor Admin ID (optional; preferred for dashboards)
        status: Filter by status (optional)
        page, limit: Pagination
    """
    # Step 1: Get query parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    filter_date = request.args.get('date', type=str)  # Format: YYYY-MM-DD
    patient_id = request.args.get('patient_id', type=str)
    doctor = request.args.get('doctor', type=str)
    doctor_id = request.args.get('doctor_id', type=int)
    status = request.args.get('status', type=str)

    # Step 1b: If current user is a doctor, default to their own appointments
    # and show only "With Doctor" by default (doctor dashboard behaviour).
    current_doctor_name = None
    current_user = None
    try:
        user_id = int(get_jwt_identity())
        current_user = Admin.query.get(user_id)
    except Exception:
        current_user = None

    if current_user and current_user.role == 'doctor':
        # Build the same display name used when creating appointments
        current_doctor_name = current_user.first_name or current_user.username
        if current_user.last_name:
            current_doctor_name = f"{current_doctor_name} {current_user.last_name}"

        # If frontend did not explicitly request another status,
        # default to showing only "With Doctor" for doctor dashboard.
        if not status:
            status = 'With Doctor'

        # If no explicit doctor/doctor_id filter was provided,
        # automatically filter by this doctor.
        if not doctor and not doctor_id:
            doctor = current_doctor_name
    
    # Step 2: Validate pagination
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
    
    # Step 3: Start building query (exclude soft-deleted - PDF spec §9)
    query = Appointment.query.filter(Appointment.deleted_at.is_(None))
    
    # Step 4: Apply date filter (default: today)
    try:
        if filter_date:
            # Parse provided date
            filter_date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
        else:
            # Default to today's date
            filter_date_obj = date.today()
        query = query.filter(Appointment.date == filter_date_obj)
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400
    
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)
    
    # Filter by doctor name (string)
    if doctor:
        query = query.filter(Appointment.doctor.ilike(f'%{doctor}%'))  # Case-insensitive search
    
    # Filter by doctor_id (Admin.id) – used by doctor dashboard
    if doctor_id:
        try:
            from app.models import Admin
            doctor_admin = Admin.query.get(doctor_id)
        except Exception:
            doctor_admin = None
        
        if doctor_admin:
            # Build display name the same way as when creating appointments
            doctor_name = doctor_admin.first_name or doctor_admin.username
            if doctor_admin.last_name:
                doctor_name = f"{doctor_name} {doctor_admin.last_name}"
            query = query.filter(Appointment.doctor == doctor_name)
    
    if status:
        query = query.filter(Appointment.status == status)
    
    # Step 5: Get total count (before pagination)
    total = query.count()
    
    # Step 6: Apply pagination and ordering
    appointments = query.order_by(
        Appointment.date.desc(),
        Appointment.time.asc()
    ).paginate(
        page=page,
        per_page=limit,
        error_out=False
    )
    
    # Step 7: Format response with full patient info per appointment
    result = []
    for apt in appointments.items:
        patient = Patient.query.filter_by(id=apt.patient_id).filter(Patient.deleted_at.is_(None)).first()
        result.append({
            'id': apt.id,
            'patient_id': apt.patient_id,
            'patient': _patient_to_dict(patient) if patient else None,
            'doctor': apt.doctor,
            'date': apt.date.isoformat() if apt.date else None,
            'time': apt.time,
            'status': apt.status,
            'accession_number': apt.accession_number,
            'requested_procedure_id': apt.requested_procedure_id,
            'scheduled_procedure_step_id': apt.scheduled_procedure_step_id,
            'created_at': apt.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'data': result,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': appointments.pages,
            'has_next': appointments.has_next,
            'has_prev': appointments.has_prev
        },
        'date': filter_date_obj.isoformat()
    }), 200


@appointment_bp.route('/with-doctor', methods=['GET'])
@jwt_required()
@require_role('doctor')
def list_with_doctor_appointments_for_consultant():
    """
    Consultant (doctor) dashboard API.
    Returns ONLY this doctor's appointments with status "With Doctor" for a given date (default: today).
    
    Query params:
        page, limit: pagination (optional, defaults: page=1, limit=20)
    """
    from app.models import Admin

    # Get current doctor user
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    if not current_user or current_user.role != 'doctor':
        return jsonify({'success': False, 'error': 'Doctor not found'}), 403

    # Build display name exactly as used when creating appointments
    doctor_name = current_user.first_name or current_user.username
    if current_user.last_name:
        doctor_name = f"{doctor_name} {current_user.last_name}"

    # Pagination (date is always today for consultant dashboard)
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)

    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20

    # Base query: this doctor, status = "With Doctor", not deleted
    query = Appointment.query.filter(
        Appointment.deleted_at.is_(None),
        Appointment.doctor == doctor_name,
        Appointment.status == 'Completed'
    )

    # Apply date filter: ALWAYS today
    filter_date_obj = date.today()
    query = query.filter(Appointment.date == filter_date_obj)

    total = query.count()

    appointments = query.order_by(
        Appointment.time.asc()
    ).paginate(page=page, per_page=limit, error_out=False)

    result = []
    for apt in appointments.items:
        patient = Patient.query.filter_by(id=apt.patient_id).filter(Patient.deleted_at.is_(None)).first()
        result.append({
            'id': apt.id,
            'patient_id': apt.patient_id,
            'patient': _patient_to_dict(patient) if patient else None,
            'doctor': apt.doctor,
            'date': apt.date.isoformat() if apt.date else None,
            'time': apt.time,
            'status': apt.status,
            'accession_number': apt.accession_number,
            'requested_procedure_id': apt.requested_procedure_id,
            'scheduled_procedure_step_id': apt.scheduled_procedure_step_id,
            'created_at': apt.created_at.isoformat()
        })

    return jsonify({
        'success': True,
        'data': result,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': appointments.pages,
            'has_next': appointments.has_next,
            'has_prev': appointments.has_prev
        },
        'date': filter_date_obj.isoformat()
    }), 200


@appointment_bp.route('/<int:appointment_id>', methods=['GET'])
@jwt_required()
def get_appointment(appointment_id):
    """
    Get single appointment by ID with full patient info.
    """
    appointment = Appointment.query.filter(
        Appointment.id == appointment_id,
        Appointment.deleted_at.is_(None)
    ).first()
    if not appointment:
        return jsonify({'success': False, 'error': 'Appointment not found'}), 404
    patient = Patient.query.filter_by(id=appointment.patient_id).filter(Patient.deleted_at.is_(None)).first()
    return jsonify({
        'success': True,
        'data': {
            'id': appointment.id,
            'patient_id': appointment.patient_id,
            'patient': _patient_to_dict(patient) if patient else None,
            'doctor': appointment.doctor,
            'date': appointment.date.isoformat() if appointment.date else None,
            'time': appointment.time,
            'status': appointment.status,
            'accession_number': appointment.accession_number,
            'requested_procedure_id': appointment.requested_procedure_id,
            'scheduled_procedure_step_id': appointment.scheduled_procedure_step_id,
            'created_at': appointment.created_at.isoformat(),
            'updated_at': appointment.updated_at.isoformat()
        }
    }), 200


@appointment_bp.route('', methods=['POST'])
@jwt_required()
@require_role('receptionist', 'doctor')
def create_appointment():
    """
    Create new appointment
    Access: receptionist, doctor
    """
    # Step 1: Get data from request
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    # Step 2: Validate required fields (doctor is now auto-filled)
    required_fields = ['patient_id', 'date', 'time']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'error': f'Field "{field}" is required'
            }), 400
    
    # Step 3: Check if patient exists and is not deleted
    patient = Patient.query.filter_by(id=data['patient_id']).filter(Patient.deleted_at.is_(None)).first()
    if not patient:
        return jsonify({
            'success': False,
            'error': f'Patient with ID {data["patient_id"]} not found'
        }), 404
    
    # Step 4: Determine doctor name automatically
    from app.models import Admin
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)

    # If current user is a doctor, use their name
    doctor_name = None
    if current_user and current_user.role == 'doctor':
        doctor_name = current_user.first_name or current_user.username
        if current_user.last_name:
            doctor_name = f"{doctor_name} {current_user.last_name}"
    else:
        # For receptionist (or others), use the single doctor of the clinic
        clinic_id = current_user.clinic_id if current_user else None
        clinic_doctor = None
        if clinic_id:
            clinic_doctor = Admin.query.filter_by(
                clinic_id=clinic_id,
                role='doctor',
                is_active=True
            ).first()
        if clinic_doctor:
            doctor_name = clinic_doctor.first_name or clinic_doctor.username
            if clinic_doctor.last_name:
                doctor_name = f"{doctor_name} {clinic_doctor.last_name}"

    if not doctor_name:
        return jsonify({
            'success': False,
            'error': 'No active doctor found for this clinic'
        }), 400

    # Step 5: Validate date format
    try:
        appointment_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400
    
    # Step 6: Validate time format (optional - check HH:MM format)
    time_str = data['time']
    if len(time_str) != 5 or time_str[2] != ':':
        return jsonify({
            'success': False,
            'error': 'Invalid time format. Use HH:MM (e.g., 10:30)'
        }), 400
    
    # Step 7: Check for duplicate appointment (same patient, doctor, date, time)
    existing = Appointment.query.filter_by(
        patient_id=data['patient_id'],
        doctor=doctor_name,
        date=appointment_date,
        time=data['time']
    ).first()
    
    if existing:
        return jsonify({
            'success': False,
            'error': 'Appointment already exists for this patient, doctor, date, and time'
        }), 400
    
    # Step 8: Create new appointment and Visit (PDF spec: One Visit = One Study = One Report)
    try:
        from app.models import Visit

        appointment = Appointment(
            patient_id=data['patient_id'],
            doctor=doctor_name,
            date=appointment_date,
            time=data['time'],
            status=data.get('status', 'Waiting')  # Default status
        )
        
        db.session.add(appointment)
        db.session.flush()  # Get appointment.id
        
        # Create Visit/Order for this appointment (PDF spec: One Visit = One Study = One Report)
        visit = Visit(
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            visit_date=appointment_date,
            visit_status='scheduled',
            exam_type='OB/GYN Ultrasound',
            modality='US',
            created_by=user_id
        )
        
        db.session.add(visit)
        db.session.commit()
        
        # Audit log
        log_audit('appointment', 'create', user_id=user_id, entity_id=str(appointment.id), details={'patient_id': appointment.patient_id, 'date': appointment.date.isoformat()})
        
        # Step 8: Return created appointment
        return jsonify({
            'success': True,
            'data': {
                'id': appointment.id,
                'patient_id': appointment.patient_id,
                'patient_name': f"{patient.first_name} {patient.last_name}",
                'doctor': appointment.doctor,
                'date': appointment.date.isoformat(),
                'time': appointment.time,
                'status': appointment.status,
                'visit_id': visit.id,
                'created_at': appointment.created_at.isoformat()
            },
            'message': 'Appointment created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to create appointment: {str(e)}'
        }), 500


@appointment_bp.route('/<int:appointment_id>', methods=['PUT'])
@jwt_required()
@require_role('receptionist', 'doctor', 'technician')
def update_appointment(appointment_id):
    """
    Update appointment information
    Access: receptionist, doctor, technician
    """
    # Step 1: Find appointment
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({
            'success': False,
            'error': 'Appointment not found'
        }), 404
    
    # Step 2: Get update data
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    # Step 3: Update fields
    try:
        # List of updatable fields: doctor, date, time only
        # Notes field does not exist on Appointment model
        updatable_fields = ['doctor', 'date', 'time']
        
        for field in updatable_fields:
            if field in data:
                if field == 'date':
                    # Parse date string
                    appointment_date = datetime.strptime(data[field], '%Y-%m-%d').date()
                    setattr(appointment, field, appointment_date)
                else:
                    setattr(appointment, field, data[field])
        
        # Note: Status is updated via separate endpoint
        # Note: patient_id should not be changed (create new appointment instead)
        # Note: Notes field does not exist - not updatable
        
        db.session.commit()
        
        # Audit log
        user_id = int(get_jwt_identity())
        log_audit('appointment', 'update', user_id=user_id, entity_id=str(appointment_id), details={'patient_id': appointment.patient_id})
        
        # Step 4: Get patient info for response
        patient = Patient.query.get(appointment.patient_id)
        
        # Step 5: Return updated appointment
        return jsonify({
            'success': True,
            'data': {
                'id': appointment.id,
                'patient_id': appointment.patient_id,
                'patient_name': f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                'doctor': appointment.doctor,
                'date': appointment.date.isoformat(),
                'time': appointment.time,
                'status': appointment.status,
                'updated_at': appointment.updated_at.isoformat()
            },
            'message': 'Appointment updated successfully'
        }), 200
        
    except ValueError as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Invalid date format: {str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update appointment: {str(e)}'
        }), 500


@appointment_bp.route('/<int:appointment_id>/status', methods=['PUT'])
@jwt_required()
@require_role('doctor', 'technician')
def update_appointment_status(appointment_id):
    """
    Update appointment status
    Access: doctor, technician
    Status values: Waiting, With Doctor, With Technician, Completed
    """
    # Step 1: Find appointment
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({
            'success': False,
            'error': 'Appointment not found'
        }), 404
    
    # Step 2: Get status from request
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    new_status = data.get('status')
    if not new_status:
        return jsonify({
            'success': False,
            'error': 'Field "status" is required'
        }), 400
    
    # Step 3: Validate status value
    valid_statuses = [
        'Waiting',
        'With Doctor',
        'With Technician',
        'Sent to DICOM',
        'Study Completed',
        'Completed',
    ]
    
    if new_status not in valid_statuses:
        return jsonify({
            'success': False,
            'error': f'Invalid status. Valid values: {", ".join(valid_statuses)}'
        }), 400
    
    # Step 4: Update status
    try:
        appointment.status = new_status
        db.session.commit()
        
        # Step 5: Get patient info
        patient = Patient.query.get(appointment.patient_id)
        
        # Step 6: Return updated appointment
        return jsonify({
            'success': True,
            'data': {
                'id': appointment.id,
                'patient_id': appointment.patient_id,
                'patient_name': f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                'status': appointment.status,
                'updated_at': appointment.updated_at.isoformat()
            },
            'message': f'Appointment status updated to {new_status}'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update status: {str(e)}'
        }), 500


@appointment_bp.route('/<int:appointment_id>', methods=['DELETE'])
@jwt_required()
@require_role('receptionist', 'doctor')
def delete_appointment(appointment_id):
    """
    Soft-delete appointment (PDF spec §9: no hard deletion of medical data).
    Access: receptionist, doctor
    """
    from datetime import datetime as dt
    appointment = Appointment.query.filter(
        Appointment.id == appointment_id,
        Appointment.deleted_at.is_(None)
    ).first()
    if not appointment:
        return jsonify({
            'success': False,
            'error': 'Appointment not found'
        }), 404
    
    appointment_info = {
        'id': appointment.id,
        'patient_id': appointment.patient_id,
        'date': appointment.date.isoformat() if appointment.date else None,
        'time': appointment.time
    }
    try:
        appointment.deleted_at = dt.utcnow()
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Appointment {appointment_id} deleted successfully',
            'data': appointment_info
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete appointment: {str(e)}'
        }), 500


@appointment_bp.route('/schedule', methods=['POST'])
@jwt_required()
@require_role('receptionist')
def schedule_appointments():
    """
    Bulk schedule appointments
    Access: receptionist only
    Body: Array of appointment objects
    """
    # Step 1: Get data from request
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Request body must be JSON'
        }), 400
    
    # Step 2: Validate that data is a list
    if not isinstance(data, list):
        return jsonify({
            'success': False,
            'error': 'Request body must be an array of appointments'
        }), 400
    
    if len(data) == 0:
        return jsonify({
            'success': False,
            'error': 'Appointments array cannot be empty'
        }), 400
    
    if len(data) > 50:  # Limit bulk operations
        return jsonify({
            'success': False,
            'error': 'Maximum 50 appointments can be scheduled at once'
        }), 400
    
    # Step 3: Validate and create appointments
    created = []
    errors = []
    
    for idx, apt_data in enumerate(data):
        try:
            # Validate required fields (doctor is required in bulk mode)
            required_fields = ['patient_id', 'doctor', 'date', 'time']
            for field in required_fields:
                if not apt_data.get(field):
                    errors.append({
                        'index': idx,
                        'error': f'Field "{field}" is required'
                    })
                    continue
            
            # Check if patient exists
            patient = Patient.query.get(apt_data['patient_id'])
            if not patient:
                errors.append({
                    'index': idx,
                    'error': f'Patient {apt_data["patient_id"]} not found'
                })
                continue
            
            # Parse date
            try:
                appointment_date = datetime.strptime(apt_data['date'], '%Y-%m-%d').date()
            except ValueError:
                errors.append({
                    'index': idx,
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                })
                continue
            
            # Check for duplicates
            existing = Appointment.query.filter_by(
                patient_id=apt_data['patient_id'],
                doctor=apt_data['doctor'],
                date=appointment_date,
                time=apt_data['time']
            ).first()
            
            if existing:
                errors.append({
                    'index': idx,
                    'error': 'Appointment already exists'
                })
                continue
            
            # Create appointment
            appointment = Appointment(
                patient_id=apt_data['patient_id'],
                doctor=apt_data['doctor'],
                date=appointment_date,
                time=apt_data['time'],
                status=apt_data.get('status', 'Waiting')
            )
            
            db.session.add(appointment)
            created.append({
                'index': idx,
                'patient_id': apt_data['patient_id'],
                'doctor': apt_data['doctor'],
                'date': apt_data['date'],
                'time': apt_data['time']
            })
            
        except Exception as e:
            errors.append({
                'index': idx,
                'error': str(e)
            })
    
    # Step 4: Commit all or rollback if errors
    if errors and len(created) == 0:
        # All failed - don't commit
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to create any appointments',
            'errors': errors
        }), 400
    
    # Commit successful ones
    db.session.commit()
    
    # Step 5: Return results
    return jsonify({
        'success': True,
        'message': f'Created {len(created)} appointment(s)',
        'data': {
            'created': created,
            'errors': errors if errors else []
        }
    }), 201

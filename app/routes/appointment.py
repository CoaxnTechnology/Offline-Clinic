from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import Appointment, Patient
from app.extensions import db
from app.utils.decorators import require_role
from datetime import datetime, date

appointment_bp = Blueprint('appointment', __name__, url_prefix='/api/appointments')


@appointment_bp.route('', methods=['GET'])
@login_required
def list_appointments():
    """
    List all appointments with filters and pagination
    Query params: date, patient_id, doctor, status, page, limit
    """
    # Step 1: Get query parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    filter_date = request.args.get('date', type=str)  # Format: YYYY-MM-DD
    patient_id = request.args.get('patient_id', type=str)
    doctor = request.args.get('doctor', type=str)
    status = request.args.get('status', type=str)
    
    # Step 2: Validate pagination
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20
    
    # Step 3: Start building query
    query = Appointment.query
    
    # Step 4: Apply filters
    if filter_date:
        try:
            # Parse date string to date object
            filter_date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
            query = query.filter(Appointment.date == filter_date_obj)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }), 400
    
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)
    
    if doctor:
        query = query.filter(Appointment.doctor.ilike(f'%{doctor}%'))  # Case-insensitive search
    
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
    
    # Step 7: Format response with patient info
    result = []
    for apt in appointments.items:
        patient = Patient.query.get(apt.patient_id)
        result.append({
            'id': apt.id,
            'patient_id': apt.patient_id,
            'patient_name': f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
            'doctor': apt.doctor,
            'department': apt.department,
            'date': apt.date.isoformat() if apt.date else None,
            'time': apt.time,
            'status': apt.status,
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
        }
    }), 200


@appointment_bp.route('/<int:appointment_id>', methods=['GET'])
@login_required
def get_appointment(appointment_id):
    """
    Get single appointment by ID
    """
    # Step 1: Find appointment by ID
    appointment = Appointment.query.get(appointment_id)
    
    # Step 2: Check if appointment exists
    if not appointment:
        return jsonify({
            'success': False,
            'error': 'Appointment not found'
        }), 404
    
    # Step 3: Get patient info
    patient = Patient.query.get(appointment.patient_id)
    
    # Step 4: Return appointment data
    return jsonify({
        'success': True,
        'data': {
            'id': appointment.id,
            'patient_id': appointment.patient_id,
            'patient': {
                'id': patient.id if patient else None,
                'name': f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
                'phone': patient.phone if patient else None
            },
            'doctor': appointment.doctor,
            'department': appointment.department,
            'date': appointment.date.isoformat() if appointment.date else None,
            'time': appointment.time,
            'status': appointment.status,
            'created_at': appointment.created_at.isoformat(),
            'updated_at': appointment.updated_at.isoformat()
        }
    }), 200


@appointment_bp.route('', methods=['POST'])
@login_required
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
    
    # Step 2: Validate required fields
    required_fields = ['patient_id', 'doctor', 'date', 'time']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'error': f'Field "{field}" is required'
            }), 400
    
    # Step 3: Check if patient exists
    patient = Patient.query.get(data['patient_id'])
    if not patient:
        return jsonify({
            'success': False,
            'error': f'Patient with ID {data["patient_id"]} not found'
        }), 404
    
    # Step 4: Validate date format
    try:
        appointment_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }), 400
    
    # Step 5: Validate time format (optional - check HH:MM format)
    time_str = data['time']
    if len(time_str) != 5 or time_str[2] != ':':
        return jsonify({
            'success': False,
            'error': 'Invalid time format. Use HH:MM (e.g., 10:30)'
        }), 400
    
    # Step 6: Check for duplicate appointment (same patient, doctor, date, time)
    existing = Appointment.query.filter_by(
        patient_id=data['patient_id'],
        doctor=data['doctor'],
        date=appointment_date,
        time=data['time']
    ).first()
    
    if existing:
        return jsonify({
            'success': False,
            'error': 'Appointment already exists for this patient, doctor, date, and time'
        }), 400
    
    # Step 7: Create new appointment
    try:
        appointment = Appointment(
            patient_id=data['patient_id'],
            doctor=data['doctor'],
            department=data.get('department'),
            date=appointment_date,
            time=data['time'],
            status=data.get('status', 'Waiting')  # Default status
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        # Step 8: Return created appointment
        return jsonify({
            'success': True,
            'data': {
                'id': appointment.id,
                'patient_id': appointment.patient_id,
                'patient_name': f"{patient.first_name} {patient.last_name}",
                'doctor': appointment.doctor,
                'department': appointment.department,
                'date': appointment.date.isoformat(),
                'time': appointment.time,
                'status': appointment.status,
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
@login_required
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
        # List of updatable fields
        updatable_fields = ['doctor', 'department', 'date', 'time']
        
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
        
        db.session.commit()
        
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
                'department': appointment.department,
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
@login_required
@require_role('doctor', 'technician')
def update_appointment_status(appointment_id):
    """
    Update appointment status
    Access: doctor, technician
    Status values: Waiting, In-Room, In-Scan, With Doctor, With Technician, Review, Completed
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
        'Waiting', 'In-Room', 'In-Scan', 'With Doctor', 
        'With Technician', 'Review', 'Completed'
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
@login_required
@require_role('receptionist', 'doctor')
def delete_appointment(appointment_id):
    """
    Delete appointment
    Access: receptionist, doctor
    """
    # Step 1: Find appointment
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({
            'success': False,
            'error': 'Appointment not found'
        }), 404
    
    # Step 2: Store info for response
    appointment_info = {
        'id': appointment.id,
        'patient_id': appointment.patient_id,
        'date': appointment.date.isoformat() if appointment.date else None,
        'time': appointment.time
    }
    
    # Step 3: Delete appointment
    try:
        db.session.delete(appointment)
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
@login_required
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
            # Validate required fields
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
                department=apt_data.get('department'),
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

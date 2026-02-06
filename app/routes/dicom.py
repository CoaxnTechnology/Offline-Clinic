"""
DICOM API Routes
Handles DICOM studies, images, MWL operations, and measurements
"""
from flask import Blueprint, request, jsonify, send_file, abort, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_
from datetime import datetime, date
import os
import logging

from app.extensions import db
from app.models import (
    Patient, Appointment, DicomImage, DicomMeasurement
)
from app.utils.decorators import require_role

logger = logging.getLogger(__name__)

# Import DICOM service functions with error handling
try:
    from app.services.dicom_service import (
        start_dicom_servers, stop_dicom_servers, get_server_status
    )
except ImportError as e:
    logger.warning(f"DICOM service import failed: {e}. DICOM endpoints may not work.")
    # Create dummy functions to prevent import errors
    def start_dicom_servers():
        pass
    def stop_dicom_servers():
        pass
    def get_server_status():
        return {'mwl_server_running': False, 'storage_server_running': False}

try:
    from app.utils.dicom_utils import create_mwl_dataset
except ImportError as e:
    logger.warning(f"DICOM utils import failed: {e}")
    def create_mwl_dataset(*args, **kwargs):
        return None

dicom_bp = Blueprint('dicom', __name__, url_prefix='/api/dicom')


@dicom_bp.route('/studies', methods=['GET'])
@jwt_required()
def list_studies():
    """
    List DICOM studies with optional filters
    
    Production-ready features:
    - Validated pagination (max 100 per page)
    - Input sanitization
    - SQL injection protection
    - Error handling with logging
    """
    """
    List DICOM studies with optional filters
    Groups images by study_instance_uid
    
    Query params:
        patient_id: Filter by patient ID
        study_date: Filter by study date (YYYY-MM-DD)
        accession_number: Filter by accession number
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
    
    Production-ready: Validated pagination, input sanitization, error handling
    """
    try:
        from sqlalchemy import func, distinct
        
        # Production: Validate and limit pagination
        try:
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid pagination parameters'
            }), 400
        
        if page < 1:
            page = 1
        if limit < 1:
            limit = 20
        if limit > 100:  # Production: Max limit
            limit = 100
        
        patient_id = request.args.get('patient_id')
        study_date_str = request.args.get('study_date')
        accession_number = request.args.get('accession_number')
        
        # Production: Validate patient_id format if provided
        if patient_id and len(patient_id) > 20:
            return jsonify({
                'success': False,
                'error': 'Invalid patient_id format'
            }), 400
        
        # Query distinct studies (group by study_instance_uid)
        query = db.session.query(
            DicomImage.study_instance_uid,
            func.min(DicomImage.id).label('id'),
            func.min(DicomImage.patient_id).label('patient_id'),
            func.min(DicomImage.study_date).label('study_date'),
            func.min(DicomImage.study_time).label('study_time'),
            func.min(DicomImage.study_description).label('study_description'),
            func.min(DicomImage.accession_number).label('accession_number'),
            func.min(DicomImage.referring_physician).label('referring_physician'),
            func.min(DicomImage.institution_name).label('institution_name'),
            func.min(DicomImage.created_at).label('created_at'),
            func.count(distinct(DicomImage.series_instance_uid)).label('series_count'),
            func.count(DicomImage.id).label('image_count')
        ).group_by(DicomImage.study_instance_uid)
        
        # Apply filters
        if patient_id:
            query = query.filter(DicomImage.patient_id == patient_id)
        
        if study_date_str:
            try:
                study_date = datetime.strptime(study_date_str, '%Y-%m-%d').date()
                query = query.filter(DicomImage.study_date == study_date)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }), 400
        
        if accession_number:
            query = query.filter(DicomImage.accession_number == accession_number)
        
        # Order by date descending
        query = query.order_by(func.min(DicomImage.study_date).desc(), func.min(DicomImage.created_at).desc())
        
        # Get total count
        total = query.count()
        
        # Pagination
        offset = (page - 1) * limit
        studies = query.offset(offset).limit(limit).all()
        
        # Format response
        studies_data = []
        for study in studies:
            patient = Patient.query.get(study.patient_id) if study.patient_id else None
            
            studies_data.append({
                'study_instance_uid': study.study_instance_uid,
                'patient_id': study.patient_id,
                'patient_name': f"{patient.first_name} {patient.last_name}" if patient else None,
                'study_date': study.study_date.isoformat() if study.study_date else None,
                'study_time': study.study_time,
                'study_description': study.study_description,
                'accession_number': study.accession_number,
                'referring_physician': study.referring_physician,
                'institution_name': study.institution_name,
                'series_count': study.series_count,
                'image_count': study.image_count,
                'created_at': study.created_at.isoformat() if study.created_at else None
            })
        
        pages = (total + limit - 1) // limit if total > 0 else 1
        
        return jsonify({
            'success': True,
            'data': studies_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': pages,
                'has_next': page < pages,
                'has_prev': page > 1
            }
        })
    
    except Exception as e:
        logger.error(f"Error listing studies: {e}", exc_info=True)
        # Production: Don't expose internal errors to client
        error_msg = 'Failed to list studies' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/studies/<study_instance_uid>', methods=['GET'])
@jwt_required()
def get_study(study_instance_uid):
    """Get detailed information about a DICOM study by study_instance_uid"""
    try:
        from sqlalchemy import func, distinct
        
        # Get first image from study to get study-level info
        study_image = DicomImage.query.filter_by(study_instance_uid=study_instance_uid).first()
        
        if not study_image:
            return jsonify({
                'success': False,
                'error': 'Study not found'
            }), 404
        
        patient = Patient.query.get(study_image.patient_id) if study_image.patient_id else None
        
        # Get series grouped by series_instance_uid
        series_query = db.session.query(
            DicomImage.series_instance_uid,
            func.min(DicomImage.modality).label('modality'),
            func.min(DicomImage.series_number).label('series_number'),
            func.min(DicomImage.series_description).label('series_description'),
            func.min(DicomImage.body_part_examined).label('body_part_examined'),
            func.min(DicomImage.manufacturer).label('manufacturer'),
            func.count(DicomImage.id).label('image_count')
        ).filter_by(study_instance_uid=study_instance_uid).group_by(DicomImage.series_instance_uid).all()
        
        series_list = []
        for series in series_query:
            series_list.append({
                'series_instance_uid': series.series_instance_uid,
                'modality': series.modality,
                'series_number': series.series_number,
                'series_description': series.series_description,
                'body_part_examined': series.body_part_examined,
                'manufacturer': series.manufacturer,
                'image_count': series.image_count
            })
        
        return jsonify({
            'success': True,
            'data': {
                'study_instance_uid': study_image.study_instance_uid,
                'patient': {
                    'id': study_image.patient_id,
                    'name': f"{patient.first_name} {patient.last_name}" if patient else None,
                    'gender': patient.gender if patient else None,
                    'birth_date': patient.birth_date.isoformat() if patient and patient.birth_date else None
                },
                'study_date': study_image.study_date.isoformat() if study_image.study_date else None,
                'study_time': study_image.study_time,
                'study_description': study_image.study_description,
                'accession_number': study_image.accession_number,
                'referring_physician': study_image.referring_physician,
                'institution_name': study_image.institution_name,
                'series': series_list,
                'created_at': study_image.created_at.isoformat() if study_image.created_at else None
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting study: {e}", exc_info=True)
        error_msg = 'Failed to get study' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/images', methods=['GET'])
@jwt_required()
def list_images():
    """
    List DICOM images with optional filters
    
    Query params:
        patient_id: Filter by patient ID
        study_instance_uid: Filter by study UID
        series_instance_uid: Filter by series UID
        modality: Filter by modality
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
    
    Production-ready: Validated pagination, SQL injection protection, error handling
    """
    try:
        # Production: Validate pagination
        try:
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid pagination parameters'
            }), 400
        
        if page < 1:
            page = 1
        if limit < 1:
            limit = 20
        if limit > 100:  # Production: Max limit
            limit = 100
        
        # Production: Validate UID formats to prevent injection
        study_instance_uid = request.args.get('study_instance_uid')
        series_instance_uid = request.args.get('series_instance_uid')
        
        if study_instance_uid and (len(study_instance_uid) > 255 or not all(c.isalnum() or c in '.-' for c in study_instance_uid)):
            return jsonify({
                'success': False,
                'error': 'Invalid study_instance_uid format'
            }), 400
        
        if series_instance_uid and (len(series_instance_uid) > 255 or not all(c.isalnum() or c in '.-' for c in series_instance_uid)):
            return jsonify({
                'success': False,
                'error': 'Invalid series_instance_uid format'
            }), 400
        patient_id = request.args.get('patient_id')
        modality = request.args.get('modality')
        
        # Production: Validate modality if provided
        if modality and len(modality) > 10:
            return jsonify({
                'success': False,
                'error': 'Invalid modality format'
            }), 400
        
        query = DicomImage.query
        
        # Apply filters
        if patient_id:
            query = query.filter(DicomImage.patient_id == patient_id)
        
        if study_instance_uid:
            query = query.filter(DicomImage.study_instance_uid == study_instance_uid)
        
        if series_instance_uid:
            query = query.filter(DicomImage.series_instance_uid == series_instance_uid)
        
        if modality:
            query = query.filter(DicomImage.modality == modality)
        
        # Order by study date descending
        query = query.order_by(DicomImage.study_date.desc(), DicomImage.instance_number.asc())
        
        # Pagination
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        images = pagination.items
        
        # Format response
        images_data = []
        for image in images:
            images_data.append(image.to_dict())
        
        return jsonify({
            'success': True,
            'data': images_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
    
    except Exception as e:
        logger.error(f"Error listing images: {e}", exc_info=True)
        error_msg = 'Failed to list images' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/images/<int:image_id>', methods=['GET'])
@jwt_required()
def get_image(image_id):
    """Get detailed information about a DICOM image"""
    try:
        image = DicomImage.query.get_or_404(image_id)
        
        # Get measurements for this image
        measurements = DicomMeasurement.query.filter_by(dicom_image_id=image_id).all()
        measurements_data = [m.to_dict() for m in measurements]
        
        return jsonify({
            'success': True,
            'data': {
                **image.to_dict(),
                'measurements': measurements_data
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting image {image_id}: {e}", exc_info=True)
        error_msg = 'Failed to get image' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/images/<int:image_id>/file', methods=['GET'])
@jwt_required()
def get_image_file(image_id):
    """Download DICOM file - Production ready with security checks"""
    try:
        image = DicomImage.query.get_or_404(image_id)
        
        # Security: Validate file path to prevent directory traversal
        file_path = os.path.abspath(image.file_path)
        if not file_path.startswith(os.path.abspath(os.getcwd())):
            logger.warning(f"Invalid file path attempt: {image.file_path}")
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 400
        
        if not os.path.exists(file_path):
            logger.warning(f"DICOM file not found: {file_path}")
            return jsonify({
                'success': False,
                'error': 'DICOM file not found'
            }), 404
        
        # Production: Add cache headers and security
        return send_file(
            file_path,
            mimetype='application/dicom',
            as_attachment=True,
            download_name=f"{image.sop_instance_uid}.dcm",
            max_age=3600  # Cache for 1 hour
        )
    
    except Exception as e:
        logger.error(f"Error serving DICOM file {image_id}: {e}", exc_info=True)
        error_msg = 'Failed to get image file' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/images/<int:image_id>/thumbnail', methods=['GET'])
@jwt_required()
def get_image_thumbnail(image_id):
    """Get thumbnail image - Production ready with caching"""
    try:
        image = DicomImage.query.get_or_404(image_id)
        
        if not image.thumbnail_path:
            return jsonify({
                'success': False,
                'error': 'Thumbnail not available'
            }), 404
        
        # Security: Validate file path
        thumb_path = os.path.abspath(image.thumbnail_path)
        if not thumb_path.startswith(os.path.abspath(os.getcwd())):
            logger.warning(f"Invalid thumbnail path attempt: {image.thumbnail_path}")
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 400
        
        if not os.path.exists(thumb_path):
            logger.warning(f"Thumbnail file not found: {thumb_path}")
            return jsonify({
                'success': False,
                'error': 'Thumbnail not found'
            }), 404
        
        # Production: Add cache headers
        return send_file(
            thumb_path,
            mimetype='image/jpeg',
            max_age=86400  # Cache for 24 hours
        )
    
    except Exception as e:
        logger.error(f"Error serving thumbnail {image_id}: {e}", exc_info=True)
        error_msg = 'Failed to get thumbnail' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/appointments/<int:appointment_id>/send-mwl', methods=['POST'])
@jwt_required()
@require_role('receptionist', 'doctor')
def send_mwl_for_appointment(appointment_id):
    # Get current user from JWT
    from app.models import Admin
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """
    Mark appointment as ready for MWL (Modality Worklist)
    This makes the appointment available in the DICOM worklist query
    Production-ready with validation and logging
    """
    try:
        # Production: Validate appointment exists
        appointment = Appointment.query.get_or_404(appointment_id)
        patient = Patient.query.get_or_404(appointment.patient_id)
        
        # Production: Check if DICOM servers are running
        status = get_server_status()
        if not status.get('mwl_server_running'):
            return jsonify({
                'success': False,
                'error': 'MWL server is not running. Please start DICOM servers first.',
                'hint': 'POST /api/dicom/server/start'
            }), 503
        
        # Production: Validate appointment date is not in past (optional check)
        if appointment.date < datetime.now().date():
            logger.warning(f"Attempted to send MWL for past appointment: {appointment_id}")
            # Still allow it, but log warning
        
        # PDF spec: generate AccessionNumber and MWL IDs once (immutable); then publish to MWL
        if appointment.accession_number is None:
            appointment.accession_number = f"ACC{appointment.id:08d}"
            appointment.requested_procedure_id = f"RQ{appointment.id:08d}"
            appointment.scheduled_procedure_step_id = f"SP{appointment.id:08d}"
        
        # Update appointment status to indicate MWL is ready
        old_status = appointment.status
        if appointment.status not in ['Waiting', 'In-Room', 'In-Scan']:
            appointment.status = 'Waiting'
        
        db.session.commit()
        from app.utils.audit import log_audit
        log_audit('appointment', 'send_mwl', user_id=current_user.id, entity_id=str(appointment_id), details={'accession_number': appointment.accession_number})
        logger.info(
            f"MWL sent for appointment {appointment_id} (patient: {patient.id}, accession={appointment.accession_number}) "
            f"by user {current_user.username}"
        )
        
        return jsonify({
            'success': True,
            'message': f'Appointment {appointment_id} is now available in MWL',
            'data': {
                'appointment_id': appointment.id,
                'patient_id': appointment.patient_id,
                'patient_name': f"{patient.first_name} {patient.last_name}",
                'accession_number': appointment.accession_number,
                'requested_procedure_id': appointment.requested_procedure_id,
                'scheduled_procedure_step_id': appointment.scheduled_procedure_step_id,
                'date': appointment.date.isoformat(),
                'time': appointment.time,
                'department': appointment.department,
                'status': appointment.status,
                'previous_status': old_status,
                'mwl_server_status': 'running'
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to send MWL for appointment {appointment_id}: {e}", exc_info=True)
        db.session.rollback()
        error_msg = 'Failed to send MWL' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/measurements', methods=['GET'])
@jwt_required()
def list_measurements():
    """
    List DICOM measurements
    
    Query params:
        patient_id: Filter by patient ID
        study_instance_uid: Filter by study UID
        measurement_type: Filter by measurement type
        page: Page number (default: 1)
        limit: Items per page (default: 20)
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        patient_id = request.args.get('patient_id')
        study_instance_uid = request.args.get('study_instance_uid')
        measurement_type = request.args.get('measurement_type')
        
        query = DicomMeasurement.query
        
        # Apply filters
        if patient_id:
            query = query.filter(DicomMeasurement.patient_id == patient_id)
        
        if study_instance_uid:
            query = query.filter(DicomMeasurement.study_instance_uid == study_instance_uid)
        
        if measurement_type:
            query = query.filter(DicomMeasurement.measurement_type == measurement_type)
        
        # Order by creation date descending
        query = query.order_by(DicomMeasurement.created_at.desc())
        
        # Pagination
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        measurements = pagination.items
        
        # Format response
        measurements_data = [m.to_dict() for m in measurements]
        
        return jsonify({
            'success': True,
            'data': measurements_data,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
    
    except Exception as e:
        logger.error(f"Error listing measurements: {e}", exc_info=True)
        error_msg = 'Failed to list measurements' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/server/status', methods=['GET'])
@jwt_required()
@require_role('doctor', 'technician')
def get_server_status_route():
    """Get DICOM server status - Production ready with detailed metrics"""
    try:
        status = get_server_status()
        
        # Production: Add additional metrics
        try:
            from app.models import DicomImage
            total_images = DicomImage.query.count()
            recent_images = DicomImage.query.filter(
                DicomImage.created_at >= datetime.now().date()
            ).count()
        except:
            total_images = None
            recent_images = None
        
        # Production: Check storage space
        try:
            import shutil
            storage_path = os.getenv('DICOM_STORAGE_PATH', 'dicom_files')
            if os.path.exists(storage_path):
                total, used, free = shutil.disk_usage(storage_path)
                storage_info = {
                    'total_gb': round(total / (1024**3), 2),
                    'used_gb': round(used / (1024**3), 2),
                    'free_gb': round(free / (1024**3), 2),
                    'usage_percent': round((used / total) * 100, 2)
                }
            else:
                storage_info = None
        except:
            storage_info = None
        
        status['metrics'] = {
            'total_images': total_images,
            'images_today': recent_images,
            'storage': storage_info
        }
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Failed to get server status: {e}", exc_info=True)
        error_msg = 'Failed to get server status' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/server/start', methods=['POST'])
@jwt_required()
@require_role('doctor', 'technician')
def start_servers():
    # Get current user from JWT
    from app.models import Admin
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """Start DICOM servers (MWL and Storage) - Production ready"""
    try:
        # Check if already running
        current_status = get_server_status()
        if current_status.get('mwl_server_running') and current_status.get('storage_server_running'):
            return jsonify({
                'success': True,
                'message': 'DICOM servers are already running',
                'data': current_status
            }), 200
        
        # Start servers
        start_dicom_servers()
        
        # Wait a moment for servers to initialize
        import time
        time.sleep(1)
        
        # Verify status
        status = get_server_status()
        
        if not status.get('mwl_server_running') or not status.get('storage_server_running'):
            return jsonify({
                'success': False,
                'error': 'Servers failed to start. Check logs for details.',
                'data': status
            }), 500
        
        logger.info(f"DICOM servers started by user {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'DICOM servers started successfully',
            'data': status
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to start DICOM servers: {e}", exc_info=True)
        error_msg = 'Failed to start servers. Check logs for details.' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/server/stop', methods=['POST'])
@jwt_required()
@require_role('doctor', 'technician')
def stop_servers():
    # Get current user from JWT
    from app.models import Admin
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """Stop DICOM servers - Production ready with graceful shutdown"""
    try:
        logger.info(f"DICOM servers stop requested by user {current_user.username}")
        
        # Check current status
        status_before = get_server_status()
        
        stop_dicom_servers()
        
        # Wait a moment and verify
        import time
        time.sleep(0.5)
        status_after = get_server_status()
        
        if status_after.get('mwl_server_running') or status_after.get('storage_server_running'):
            logger.warning("Some servers may still be running after stop request")
            return jsonify({
                'success': False,
                'error': 'Servers may still be running. Check status.',
                'data': status_after
            }), 500
        
        logger.info("DICOM servers stopped successfully")
        
        return jsonify({
            'success': True,
            'message': 'DICOM servers stopped successfully',
            'data': {
                'before': status_before,
                'after': status_after
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to stop DICOM servers: {e}", exc_info=True)
        error_msg = 'Failed to stop servers' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@dicom_bp.route('/patients/<patient_id>/studies', methods=['GET'])
@jwt_required()
def get_patient_studies(patient_id):
    """Get all DICOM studies for a specific patient - Production ready"""
    try:
        from sqlalchemy import func, distinct
        
        # Production: Validate patient_id format
        if len(patient_id) > 20:
            return jsonify({
                'success': False,
                'error': 'Invalid patient_id format'
            }), 400
        
        patient = Patient.query.get_or_404(patient_id)
        
        # Group by study_instance_uid
        studies_query = db.session.query(
            DicomImage.study_instance_uid,
            func.min(DicomImage.study_date).label('study_date'),
            func.min(DicomImage.study_time).label('study_time'),
            func.min(DicomImage.study_description).label('study_description'),
            func.min(DicomImage.accession_number).label('accession_number'),
            func.min(DicomImage.created_at).label('created_at'),
            func.count(distinct(DicomImage.series_instance_uid)).label('series_count'),
            func.count(DicomImage.id).label('image_count')
        ).filter_by(patient_id=patient_id).group_by(DicomImage.study_instance_uid)\
            .order_by(func.min(DicomImage.study_date).desc()).all()
        
        studies_data = []
        for study in studies_query:
            studies_data.append({
                'study_instance_uid': study.study_instance_uid,
                'study_date': study.study_date.isoformat() if study.study_date else None,
                'study_time': study.study_time,
                'study_description': study.study_description,
                'accession_number': study.accession_number,
                'series_count': study.series_count,
                'image_count': study.image_count,
                'created_at': study.created_at.isoformat() if study.created_at else None
            })
        
        return jsonify({
            'success': True,
            'data': studies_data,
            'patient': {
                'id': patient.id,
                'name': f"{patient.first_name} {patient.last_name}"
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting patient studies: {e}", exc_info=True)
        error_msg = 'Failed to get patient studies' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

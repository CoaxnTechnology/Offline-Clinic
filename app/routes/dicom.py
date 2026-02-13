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
from app.models import Patient, Appointment, DicomImage, DicomMeasurement
from app.utils.decorators import require_role

logger = logging.getLogger(__name__)

# Import DICOM service functions with error handling
try:
    from app.services.dicom_service import (
        start_dicom_servers,
        stop_dicom_servers,
        get_server_status,
    )
except ImportError as e:
    logger.warning(f"DICOM service import failed: {e}. DICOM endpoints may not work.")

    # Create dummy functions to prevent import errors
    def start_dicom_servers():
        pass

    def stop_dicom_servers():
        pass

    def get_server_status():
        return {"mwl_server_running": False, "storage_server_running": False}


try:
    from app.utils.dicom_utils import create_mwl_dataset
except ImportError as e:
    logger.warning(f"DICOM utils import failed: {e}")

    def create_mwl_dataset(*args, **kwargs):
        return None


dicom_bp = Blueprint("dicom", __name__, url_prefix="/api/dicom")


@dicom_bp.route("/studies", methods=["GET"])
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
            page = request.args.get("page", 1, type=int)
            limit = request.args.get("limit", 20, type=int)
        except (ValueError, TypeError):
            return jsonify(
                {"success": False, "error": "Invalid pagination parameters"}
            ), 400

        if page < 1:
            page = 1
        if limit < 1:
            limit = 20
        if limit > 100:  # Production: Max limit
            limit = 100

        patient_id = request.args.get("patient_id")
        study_date_str = request.args.get("study_date")
        accession_number = request.args.get("accession_number")
        appointment_id = request.args.get("appointment_id", type=int)
        visit_id = request.args.get("visit_id", type=int)

        # Production: Validate patient_id format if provided
        if patient_id and len(patient_id) > 20:
            return jsonify(
                {"success": False, "error": "Invalid patient_id format"}
            ), 400

        # Query distinct studies (group by study_instance_uid)
        query = db.session.query(
            DicomImage.study_instance_uid,
            func.min(DicomImage.id).label("id"),
            func.min(DicomImage.patient_id).label("patient_id"),
            func.min(DicomImage.study_date).label("study_date"),
            func.min(DicomImage.study_time).label("study_time"),
            func.min(DicomImage.study_description).label("study_description"),
            func.min(DicomImage.accession_number).label("accession_number"),
            func.min(DicomImage.referring_physician).label("referring_physician"),
            func.min(DicomImage.institution_name).label("institution_name"),
            func.min(DicomImage.created_at).label("created_at"),
            func.min(DicomImage.appointment_id).label("appointment_id"),
            func.min(DicomImage.visit_id).label("visit_id"),
            func.count(distinct(DicomImage.series_instance_uid)).label("series_count"),
            func.count(DicomImage.id).label("image_count"),
        ).group_by(DicomImage.study_instance_uid)

        # Apply filters
        if patient_id:
            query = query.filter(DicomImage.patient_id == patient_id)

        if study_date_str:
            try:
                study_date = datetime.strptime(study_date_str, "%Y-%m-%d").date()
                query = query.filter(DicomImage.study_date == study_date)
            except ValueError:
                return jsonify(
                    {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
                ), 400

        if accession_number:
            query = query.filter(DicomImage.accession_number == accession_number)

        if appointment_id:
            query = query.filter(DicomImage.appointment_id == appointment_id)

        if visit_id:
            query = query.filter(DicomImage.visit_id == visit_id)

        # Order by date descending
        query = query.order_by(
            func.min(DicomImage.study_date).desc(),
            func.min(DicomImage.created_at).desc(),
        )

        # Get total count
        total = query.count()

        # Pagination
        offset = (page - 1) * limit
        studies = query.offset(offset).limit(limit).all()

        # Format response
        studies_data = []
        for study in studies:
            patient = Patient.query.get(study.patient_id) if study.patient_id else None

            studies_data.append(
                {
                    "study_instance_uid": study.study_instance_uid,
                    "patient_id": study.patient_id,
                    "patient_name": f"{patient.first_name} {patient.last_name}"
                    if patient
                    else None,
                    "study_date": study.study_date.isoformat()
                    if study.study_date
                    else None,
                    "study_time": study.study_time,
                    "study_description": study.study_description,
                    "accession_number": study.accession_number,
                    "referring_physician": study.referring_physician,
                    "institution_name": study.institution_name,
                    "series_count": study.series_count,
                    "image_count": study.image_count,
                    "created_at": study.created_at.isoformat()
                    if study.created_at
                    else None,
                }
            )

        pages = (total + limit - 1) // limit if total > 0 else 1

        return jsonify(
            {
                "success": True,
                "data": studies_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": pages,
                    "has_next": page < pages,
                    "has_prev": page > 1,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error listing studies: {e}", exc_info=True)
        # Production: Don't expose internal errors to client
        error_msg = "Failed to list studies" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/studies/<study_instance_uid>", methods=["GET"])
@jwt_required()
def get_study(study_instance_uid):
    """Get detailed information about a DICOM study by study_instance_uid"""
    try:
        from sqlalchemy import func, distinct

        # Get first image from study to get study-level info
        study_image = DicomImage.query.filter_by(
            study_instance_uid=study_instance_uid
        ).first()

        if not study_image:
            return jsonify({"success": False, "error": "Study not found"}), 404

        patient = (
            Patient.query.get(study_image.patient_id)
            if study_image.patient_id
            else None
        )

        # Get series grouped by series_instance_uid
        series_query = (
            db.session.query(
                DicomImage.series_instance_uid,
                func.min(DicomImage.modality).label("modality"),
                func.min(DicomImage.series_number).label("series_number"),
                func.min(DicomImage.series_description).label("series_description"),
                func.min(DicomImage.body_part_examined).label("body_part_examined"),
                func.min(DicomImage.manufacturer).label("manufacturer"),
                func.count(DicomImage.id).label("image_count"),
            )
            .filter_by(study_instance_uid=study_instance_uid)
            .group_by(DicomImage.series_instance_uid)
            .all()
        )

        series_list = []
        for series in series_query:
            series_list.append(
                {
                    "series_instance_uid": series.series_instance_uid,
                    "modality": series.modality,
                    "series_number": series.series_number,
                    "series_description": series.series_description,
                    "body_part_examined": series.body_part_examined,
                    "manufacturer": series.manufacturer,
                    "image_count": series.image_count,
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "study_instance_uid": study_image.study_instance_uid,
                    "patient": {
                        "id": study_image.patient_id,
                        "name": f"{patient.first_name} {patient.last_name}"
                        if patient
                        else None,
                        "gender": patient.gender if patient else None,
                        "birth_date": patient.birth_date.isoformat()
                        if patient and patient.birth_date
                        else None,
                    },
                    "study_date": study_image.study_date.isoformat()
                    if study_image.study_date
                    else None,
                    "study_time": study_image.study_time,
                    "study_description": study_image.study_description,
                    "accession_number": study_image.accession_number,
                    "referring_physician": study_image.referring_physician,
                    "institution_name": study_image.institution_name,
                    "series": series_list,
                    "created_at": study_image.created_at.isoformat()
                    if study_image.created_at
                    else None,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting study: {e}", exc_info=True)
        error_msg = "Failed to get study" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/images", methods=["GET"])
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
            page = request.args.get("page", 1, type=int)
            limit = request.args.get("limit", 20, type=int)
        except (ValueError, TypeError):
            return jsonify(
                {"success": False, "error": "Invalid pagination parameters"}
            ), 400

        if page < 1:
            page = 1
        if limit < 1:
            limit = 20
        if limit > 100:  # Production: Max limit
            limit = 100

        # Production: Validate UID formats to prevent injection
        study_instance_uid = request.args.get("study_instance_uid")
        series_instance_uid = request.args.get("series_instance_uid")

        if study_instance_uid and (
            len(study_instance_uid) > 255
            or not all(c.isalnum() or c in ".-" for c in study_instance_uid)
        ):
            return jsonify(
                {"success": False, "error": "Invalid study_instance_uid format"}
            ), 400

        if series_instance_uid and (
            len(series_instance_uid) > 255
            or not all(c.isalnum() or c in ".-" for c in series_instance_uid)
        ):
            return jsonify(
                {"success": False, "error": "Invalid series_instance_uid format"}
            ), 400
        patient_id = request.args.get("patient_id")
        modality = request.args.get("modality")
        appointment_id = request.args.get("appointment_id", type=int)
        visit_id = request.args.get("visit_id", type=int)

        # Production: Validate modality if provided
        if modality and len(modality) > 10:
            return jsonify({"success": False, "error": "Invalid modality format"}), 400

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

        if appointment_id:
            query = query.filter(DicomImage.appointment_id == appointment_id)

        if visit_id:
            query = query.filter(DicomImage.visit_id == visit_id)

        # Order by study date descending
        query = query.order_by(
            DicomImage.study_date.desc(), DicomImage.instance_number.asc()
        )

        # Pagination
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        images = pagination.items

        # Format response
        images_data = []
        for image in images:
            images_data.append(image.to_dict())

        return jsonify(
            {
                "success": True,
                "data": images_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error listing images: {e}", exc_info=True)
        error_msg = "Failed to list images" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/images/<int:image_id>", methods=["GET"])
@jwt_required()
def get_image(image_id):
    """Get detailed information about a DICOM image"""
    try:
        image = DicomImage.query.get_or_404(image_id)

        # Get measurements for this image
        measurements = DicomMeasurement.query.filter_by(dicom_image_id=image_id).all()
        measurements_data = [m.to_dict() for m in measurements]

        return jsonify(
            {
                "success": True,
                "data": {**image.to_dict(), "measurements": measurements_data},
            }
        )

    except Exception as e:
        logger.error(f"Error getting image {image_id}: {e}", exc_info=True)
        error_msg = "Failed to get image" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/images/<int:image_id>/file", methods=["GET"])
@jwt_required()
def get_image_file(image_id):
    """Download DICOM file - Production ready with security checks"""
    try:
        image = DicomImage.query.get_or_404(image_id)

        # Security: Validate file path to prevent directory traversal
        file_path = os.path.abspath(image.file_path)
        if not file_path.startswith(os.path.abspath(os.getcwd())):
            logger.warning(f"Invalid file path attempt: {image.file_path}")
            return jsonify({"success": False, "error": "Invalid file path"}), 400

        if not os.path.exists(file_path):
            logger.warning(f"DICOM file not found: {file_path}")
            return jsonify({"success": False, "error": "DICOM file not found"}), 404

        # Production: Add cache headers and security
        return send_file(
            file_path,
            mimetype="application/dicom",
            as_attachment=True,
            download_name=f"{image.sop_instance_uid}.dcm",
            max_age=3600,  # Cache for 1 hour
        )

    except Exception as e:
        logger.error(f"Error serving DICOM file {image_id}: {e}", exc_info=True)
        error_msg = "Failed to get image file" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/images/<int:image_id>/thumbnail", methods=["GET"])
@jwt_required()
def get_image_thumbnail(image_id):
    """Get thumbnail image - Production ready with caching"""
    try:
        image = DicomImage.query.get_or_404(image_id)

        if not image.thumbnail_path:
            return jsonify({"success": False, "error": "Thumbnail not available"}), 404

        # Security: Validate file path
        thumb_path = os.path.abspath(image.thumbnail_path)
        if not thumb_path.startswith(os.path.abspath(os.getcwd())):
            logger.warning(f"Invalid thumbnail path attempt: {image.thumbnail_path}")
            return jsonify({"success": False, "error": "Invalid file path"}), 400

        if not os.path.exists(thumb_path):
            logger.warning(f"Thumbnail file not found: {thumb_path}")
            return jsonify({"success": False, "error": "Thumbnail not found"}), 404

        # Production: Add cache headers
        return send_file(
            thumb_path,
            mimetype="image/jpeg",
            max_age=86400,  # Cache for 24 hours
        )

    except Exception as e:
        logger.error(f"Error serving thumbnail {image_id}: {e}", exc_info=True)
        error_msg = "Failed to get thumbnail" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/appointments/<int:appointment_id>/send-mwl", methods=["POST"])
@jwt_required()
@require_role("receptionist", "doctor")
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
        if not status.get("mwl_server_running"):
            return jsonify(
                {
                    "success": False,
                    "error": "MWL server is not running. Please start DICOM servers first.",
                    "hint": "POST /api/dicom/server/start",
                }
            ), 503

        # Production: Validate appointment date is not in past (optional check)
        if appointment.date < datetime.now().date():
            logger.warning(
                f"Attempted to send MWL for past appointment: {appointment_id}"
            )
            # Still allow it, but log warning

        # PDF spec: generate AccessionNumber and MWL IDs once (immutable); then publish to MWL
        from app.models import Visit

        # Get or create Visit for this appointment (PDF spec: One Visit = One Study = One Report)
        visit = Visit.query.filter_by(appointment_id=appointment_id).first()
        if not visit:
            visit = Visit(
                appointment_id=appointment_id,
                patient_id=appointment.patient_id,
                visit_date=appointment.date,
                visit_status="scheduled",
                exam_type="OB/GYN Ultrasound",
                modality="US",
                created_by=current_user.id,
            )
            db.session.add(visit)
            db.session.flush()

        # Generate AccessionNumber if not already set
        if appointment.accession_number is None:
            appointment.accession_number = f"ACC{appointment.id:08d}"
            appointment.requested_procedure_id = f"RQ{appointment.id:08d}"
            appointment.scheduled_procedure_step_id = f"SP{appointment.id:08d}"

        # Update Visit with AccessionNumber and DICOM IDs
        visit.accession_number = appointment.accession_number
        visit.requested_procedure_id = appointment.requested_procedure_id
        visit.scheduled_procedure_step_id = appointment.scheduled_procedure_step_id
        visit.visit_status = "in_progress"

        # Update appointment status to indicate MWL is ready
        old_status = appointment.status
        appointment.status = "Sent to DICOM"
        appointment.updated_at = datetime.utcnow()

        db.session.commit()
        from app.utils.audit import log_audit

        log_audit(
            "appointment",
            "send_mwl",
            user_id=current_user.id,
            entity_id=str(appointment_id),
            details={"accession_number": appointment.accession_number},
        )
        logger.info(
            f"MWL sent for appointment {appointment_id} (patient: {patient.id}, accession={appointment.accession_number}) "
            f"by user {current_user.username}"
        )

        return jsonify(
            {
                "success": True,
                "message": f"Appointment {appointment_id} is now available in MWL",
                "data": {
                    "appointment_id": appointment.id,
                    "patient_id": appointment.patient_id,
                    "patient_name": f"{patient.first_name} {patient.last_name}",
                    "accession_number": appointment.accession_number,
                    "requested_procedure_id": appointment.requested_procedure_id,
                    "scheduled_procedure_step_id": appointment.scheduled_procedure_step_id,
                    "date": appointment.date.isoformat(),
                    "time": appointment.time,
                    "status": appointment.status,
                    "previous_status": old_status,
                    "mwl_server_status": "running",
                },
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to send MWL for appointment {appointment_id}: {e}", exc_info=True
        )
        db.session.rollback()
        error_msg = "Failed to send MWL"
        detail = str(e)
        return jsonify(
            {
                "success": False,
                "error": error_msg,
                "detail": detail,
            }
        ), 500


@dicom_bp.route("/measurements", methods=["GET"])
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
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 20, type=int)
        patient_id = request.args.get("patient_id")
        study_instance_uid = request.args.get("study_instance_uid")
        measurement_type = request.args.get("measurement_type")

        query = DicomMeasurement.query

        # Apply filters
        if patient_id:
            query = query.filter(DicomMeasurement.patient_id == patient_id)

        if study_instance_uid:
            query = query.filter(
                DicomMeasurement.study_instance_uid == study_instance_uid
            )

        if measurement_type:
            query = query.filter(DicomMeasurement.measurement_type == measurement_type)

        # Order by creation date descending
        query = query.order_by(DicomMeasurement.created_at.desc())

        # Pagination
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        measurements = pagination.items

        # Format response
        measurements_data = [m.to_dict() for m in measurements]

        return jsonify(
            {
                "success": True,
                "data": measurements_data,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "has_next": pagination.has_next,
                    "has_prev": pagination.has_prev,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error listing measurements: {e}", exc_info=True)
        error_msg = "Failed to list measurements" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/server/status", methods=["GET"])
@jwt_required()
@require_role("doctor", "technician")
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

            storage_path = os.getenv("DICOM_STORAGE_PATH", "dicom_files")
            if os.path.exists(storage_path):
                total, used, free = shutil.disk_usage(storage_path)
                storage_info = {
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                    "usage_percent": round((used / total) * 100, 2),
                }
            else:
                storage_info = None
        except:
            storage_info = None

        status["metrics"] = {
            "total_images": total_images,
            "images_today": recent_images,
            "storage": storage_info,
        }

        return jsonify(
            {
                "success": True,
                "data": status,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Failed to get server status: {e}", exc_info=True)
        error_msg = "Failed to get server status" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/server/start", methods=["POST"])
@jwt_required()
@require_role("doctor", "technician")
def start_servers():
    """Start DICOM servers (MWL and Storage) - Production ready"""
    # Get current user from JWT
    from app.models import Admin

    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)

    logger.info(
        f"DICOM start requested by user {current_user.username} with role {current_user.role}"
    )

    try:
        # Check if already running
        current_status = get_server_status()
        if current_status.get("mwl_server_running") and current_status.get(
            "storage_server_running"
        ):
            return jsonify(
                {
                    "success": True,
                    "message": "DICOM servers are already running",
                    "data": current_status,
                }
            ), 200

        # Start servers (pass app so MWL handler has app context in background thread)
        from flask import current_app

        start_dicom_servers(current_app._get_current_object())

        # Wait a moment for servers to initialize
        import time

        time.sleep(1)

        # Verify status
        status = get_server_status()

        if not status.get("mwl_server_running") or not status.get(
            "storage_server_running"
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "Servers failed to start. Check logs for details.",
                    "data": status,
                }
            ), 500

        logger.info(f"DICOM servers started by user {current_user.username}")

        return jsonify(
            {
                "success": True,
                "message": "DICOM servers started successfully",
                "data": status,
            }
        ), 200

    except Exception as e:
        logger.error(f"Failed to start DICOM servers: {e}", exc_info=True)
        error_msg = (
            "Failed to start servers. Check logs for details."
            if not current_app.debug
            else str(e)
        )
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/server/diagnose", methods=["GET"])
def diagnose_servers():
    """Diagnose DICOM server issues - No authentication required for debugging"""
    try:
        from app.services.dicom_service import get_server_status

        # Get current status
        status = get_server_status()

        # Test starting servers without Flask context issues
        test_result = {}
        try:
            from app.services.dicom_service import start_dicom_servers
            from flask import current_app

            start_dicom_servers(current_app._get_current_object())
            test_result["start_test"] = "SUCCESS"
            # Get status after start
            status_after = get_server_status()
            test_result["status_after_start"] = status_after
        except Exception as e:
            test_result["start_test"] = f"FAILED: {str(e)}"
            import traceback

            test_result["traceback"] = traceback.format_exc()

        return jsonify(
            {
                "success": True,
                "data": {
                    "current_status": status,
                    "start_test": test_result,
                    "environment": {
                        "AUTO_START_DICOM": os.getenv("AUTO_START_DICOM", "not_set"),
                        "FLASK_ENV": os.getenv("FLASK_ENV", "not_set"),
                        "CI": os.getenv("CI", "not_set"),
                        "GITHUB_ACTIONS": os.getenv("GITHUB_ACTIONS", "not_set"),
                    },
                },
            }
        ), 200

    except Exception as e:
        logger.error(f"Diagnosis failed: {e}", exc_info=True)
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
                if "traceback" in locals()
                else None,
            }
        ), 500


@dicom_bp.route("/server/stop", methods=["POST"])
@jwt_required()
@require_role("doctor", "technician")
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

        if status_after.get("mwl_server_running") or status_after.get(
            "storage_server_running"
        ):
            logger.warning("Some servers may still be running after stop request")
            return jsonify(
                {
                    "success": False,
                    "error": "Servers may still be running. Check status.",
                    "data": status_after,
                }
            ), 500

        logger.info("DICOM servers stopped successfully")

        return jsonify(
            {
                "success": True,
                "message": "DICOM servers stopped successfully",
                "data": {"before": status_before, "after": status_after},
            }
        )

    except Exception as e:
        logger.error(f"Failed to stop DICOM servers: {e}", exc_info=True)
        error_msg = "Failed to stop servers" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/patients/<patient_id>/studies", methods=["GET"])
@jwt_required()
def get_patient_studies(patient_id):
    """Get all DICOM studies for a specific patient - Production ready"""
    try:
        from sqlalchemy import func, distinct

        # Production: Validate patient_id format
        if len(patient_id) > 20:
            return jsonify(
                {"success": False, "error": "Invalid patient_id format"}
            ), 400

        patient = Patient.query.get_or_404(patient_id)

        # Group by study_instance_uid
        studies_query = (
            db.session.query(
                DicomImage.study_instance_uid,
                func.min(DicomImage.study_date).label("study_date"),
                func.min(DicomImage.study_time).label("study_time"),
                func.min(DicomImage.study_description).label("study_description"),
                func.min(DicomImage.accession_number).label("accession_number"),
                func.min(DicomImage.created_at).label("created_at"),
                func.count(distinct(DicomImage.series_instance_uid)).label(
                    "series_count"
                ),
                func.count(DicomImage.id).label("image_count"),
            )
            .filter_by(patient_id=patient_id)
            .group_by(DicomImage.study_instance_uid)
            .order_by(func.min(DicomImage.study_date).desc())
            .all()
        )

        studies_data = []
        for study in studies_query:
            studies_data.append(
                {
                    "study_instance_uid": study.study_instance_uid,
                    "study_date": study.study_date.isoformat()
                    if study.study_date
                    else None,
                    "study_time": study.study_time,
                    "study_description": study.study_description,
                    "accession_number": study.accession_number,
                    "series_count": study.series_count,
                    "image_count": study.image_count,
                    "created_at": study.created_at.isoformat()
                    if study.created_at
                    else None,
                }
            )

        return jsonify(
            {
                "success": True,
                "data": studies_data,
                "patient": {
                    "id": patient.id,
                    "name": f"{patient.first_name} {patient.last_name}",
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting patient studies: {e}", exc_info=True)
        error_msg = "Failed to get patient studies" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/studies/<study_instance_uid>/full", methods=["GET"])
@jwt_required()
def get_study_full(study_instance_uid):
    """
    Get full study details with appointment and patient information.

    Safety: Uses accession_number as immutable link key. Validates patient_id
    consistency across all tables to prevent data from being attached to wrong patient.

    Query params:
        validate_patient: If provided, validates study belongs to this patient_id
    """
    try:
        from sqlalchemy import func, distinct
        from app.models import Visit, Appointment

        validate_patient_id = request.args.get("validate_patient")

        study_image = DicomImage.query.filter_by(
            study_instance_uid=study_instance_uid
        ).first()

        if not study_image:
            return jsonify({"success": False, "error": "Study not found"}), 404

        accession_number = study_image.accession_number
        dicom_patient_id = study_image.patient_id

        if not accession_number:
            return jsonify(
                {
                    "success": False,
                    "error": "Study has no accession_number - cannot link to appointment",
                }
            ), 400

        visit = None
        appointment = None
        patient = None
        patient_link_verified = False

        if accession_number:
            visit = Visit.query.filter_by(accession_number=accession_number).first()

            if visit:
                appointment = (
                    Appointment.query.get(visit.appointment_id)
                    if visit.appointment_id
                    else None
                )

                if appointment and appointment.patient_id:
                    patient = Patient.query.get(appointment.patient_id)

                    if patient:
                        dicom_patient_id_str = (
                            str(dicom_patient_id) if dicom_patient_id else None
                        )
                        appointment_patient_id_str = str(appointment.patient_id)

                        patient_link_verified = (
                            dicom_patient_id_str == appointment_patient_id_str
                        )

                        if (
                            validate_patient_id
                            and str(validate_patient_id) != appointment_patient_id_str
                        ):
                            logger.warning(
                                f"Patient ID mismatch: validate_patient={validate_patient_id}, "
                                f"appointment patient_id={appointment_patient_id_str}, "
                                f"dicom patient_id={dicom_patient_id_str}"
                            )
                            return jsonify(
                                {
                                    "success": False,
                                    "error": f"Study does not belong to patient {validate_patient_id}",
                                }
                            ), 403

        series_query = (
            db.session.query(
                DicomImage.series_instance_uid,
                func.min(DicomImage.modality).label("modality"),
                func.min(DicomImage.series_number).label("series_number"),
                func.min(DicomImage.series_description).label("series_description"),
                func.min(DicomImage.series_date).label("series_date"),
                func.min(DicomImage.body_part_examined).label("body_part_examined"),
                func.min(DicomImage.manufacturer).label("manufacturer"),
                func.count(DicomImage.id).label("image_count"),
            )
            .filter_by(study_instance_uid=study_instance_uid)
            .group_by(DicomImage.series_instance_uid)
            .all()
        )

        series_list = []
        for series in series_query:
            images = (
                DicomImage.query.filter_by(
                    study_instance_uid=study_instance_uid,
                    series_instance_uid=series.series_instance_uid,
                )
                .order_by(DicomImage.instance_number.asc())
                .all()
            )

            images_data = []
            for img in images:
                images_data.append(
                    {
                        "id": img.id,
                        "sop_instance_uid": img.sop_instance_uid,
                        "instance_number": img.instance_number,
                        "thumbnail_path": img.thumbnail_path,
                        "file_path": img.file_path,
                    }
                )

            series_list.append(
                {
                    "series_instance_uid": series.series_instance_uid,
                    "modality": series.modality,
                    "series_number": series.series_number,
                    "series_description": series.series_description,
                    "series_date": series.series_date.isoformat()
                    if series.series_date
                    else None,
                    "body_part_examined": series.body_part_examined,
                    "manufacturer": series.manufacturer,
                    "image_count": series.image_count,
                    "images": images_data,
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "study": {
                        "study_instance_uid": study_image.study_instance_uid,
                        "study_date": study_image.study_date.isoformat()
                        if study_image.study_date
                        else None,
                        "study_time": study_image.study_time,
                        "study_description": study_image.study_description,
                        "accession_number": accession_number,
                        "referring_physician": study_image.referring_physician,
                        "institution_name": study_image.institution_name,
                        "created_at": study_image.created_at.isoformat()
                        if study_image.created_at
                        else None,
                    },
                    "patient": {
                        "id": patient.id if patient else None,
                        "patient_id": patient.patient_id
                        if patient
                        else dicom_patient_id,
                        "first_name": patient.first_name if patient else None,
                        "last_name": patient.last_name if patient else None,
                        "gender": patient.gender if patient else None,
                        "birth_date": patient.birth_date.isoformat()
                        if patient and patient.birth_date
                        else None,
                        "phone": patient.phone if patient else None,
                    }
                    if patient
                    else {
                        "id": None,
                        "patient_id": dicom_patient_id,
                        "first_name": None,
                        "last_name": study_image.patient_name,
                        "gender": study_image.patient_sex,
                        "birth_date": study_image.patient_birth_date.isoformat()
                        if study_image.patient_birth_date
                        else None,
                    },
                    "appointment": {
                        "id": appointment.id if appointment else None,
                        "date": appointment.date.isoformat()
                        if appointment and appointment.date
                        else None,
                        "time": appointment.time if appointment else None,
                        "status": appointment.status if appointment else None,
                        "reason": appointment.reason if appointment else None,
                        "notes": appointment.notes if appointment else None,
                    }
                    if appointment
                    else None,
                    "visit": {
                        "id": visit.id if visit else None,
                        "visit_status": visit.visit_status if visit else None,
                        "exam_type": visit.exam_type if visit else None,
                        "modality": visit.modality if visit else None,
                        "study_instance_uid": visit.study_instance_uid
                        if visit
                        else None,
                    }
                    if visit
                    else None,
                    "series": series_list,
                    "_meta": {
                        "patient_link_verified": patient_link_verified,
                        "dicom_patient_id": dicom_patient_id,
                        "linked_patient_id": patient.patient_id if patient else None,
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting full study: {e}", exc_info=True)
        error_msg = "Failed to get full study" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/appointments/<int:appointment_id>/study", methods=["GET"])
@jwt_required()
def get_study_by_appointment(appointment_id):
    """
    Get DICOM study for a specific appointment.

    Safety: Uses appointment_id to look up visit, then validates the study
    belongs to the correct patient via accession_number matching.
    """
    try:
        from app.models import Visit

        appointment = Appointment.query.get_or_404(appointment_id)
        patient = Patient.query.get_or_404(appointment.patient_id)

        visit = Visit.query.filter_by(appointment_id=appointment_id).first()

        if not visit or not visit.accession_number:
            return jsonify(
                {"success": False, "error": "No DICOM study found for this appointment"}
            ), 404

        study_image = DicomImage.query.filter_by(
            accession_number=visit.accession_number
        ).first()

        if not study_image:
            return jsonify(
                {
                    "success": False,
                    "error": "DICOM study not found for this appointment's accession number",
                }
            ), 404

        dicom_patient_id = (
            str(study_image.patient_id) if study_image.patient_id else None
        )
        appointment_patient_id = str(patient.patient_id)

        if dicom_patient_id and dicom_patient_id != appointment_patient_id:
            logger.error(
                f"PATIENT MISMATCH: DICOM study patient_id={dicom_patient_id} "
                f"does not match appointment patient_id={appointment_patient_id}"
            )
            return jsonify(
                {
                    "success": False,
                    "error": "Data integrity error: study belongs to different patient",
                }
            ), 500

        return jsonify(
            {
                "success": True,
                "data": {
                    "study_instance_uid": study_image.study_instance_uid,
                    "accession_number": study_image.accession_number,
                    "study_date": study_image.study_date.isoformat()
                    if study_image.study_date
                    else None,
                    "modality": study_image.modality,
                    "patient": {
                        "id": patient.id,
                        "patient_id": patient.patient_id,
                        "name": f"{patient.first_name} {patient.last_name}",
                    },
                    "appointment": {
                        "id": appointment.id,
                        "date": appointment.date.isoformat()
                        if appointment.date
                        else None,
                        "time": appointment.time,
                        "status": appointment.status,
                    },
                    "visit": {
                        "id": visit.id,
                        "visit_status": visit.visit_status,
                        "exam_type": visit.exam_type,
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting study by appointment: {e}", exc_info=True)

        # Check what went wrong for better error message
        try:
            appointment_exists = Appointment.query.get(appointment_id) is not None
            visit_exists = (
                Visit.query.filter_by(appointment_id=appointment_id).first() is not None
                if appointment_exists
                else False
            )
            visit = (
                Visit.query.filter_by(appointment_id=appointment_id).first()
                if appointment_exists
                else None
            )
            has_accession = visit.accession_number is not None if visit else False
            has_images = (
                DicomImage.query.filter_by(appointment_id=appointment_id).count() > 0
                if appointment_exists
                else False
            )

            error_details = {
                "appointment_exists": appointment_exists,
                "visit_exists": visit_exists,
                "has_accession_number": has_accession,
                "has_dicom_images": has_images,
                "appointment_id": appointment_id,
            }
            logger.error(f"Study lookup debug: {error_details}")

            if not appointment_exists:
                error_msg = f"Appointment {appointment_id} not found"
            elif not visit_exists:
                error_msg = f"No visit found for appointment {appointment_id}"
            elif not has_accession:
                error_msg = f"No accession number for appointment {appointment_id}"
            elif not has_images:
                error_msg = f"No DICOM images received for appointment {appointment_id}"
            else:
                error_msg = "Failed to get study"
        except Exception as debug_e:
            error_msg = f"Failed to get study: {str(e)}"

        return jsonify({"success": False, "error": error_msg}), 500


@dicom_bp.route("/appointments/<int:appointment_id>/images", methods=["GET"])
@jwt_required()
def get_images_by_appointment(appointment_id):
    """
    Get all DICOM images for a specific appointment.

    Safety: Validates patient_id consistency across DicomImage → Visit → Appointment
    to prevent images from being attached to wrong patient.
    """
    try:
        from app.models import Visit

        appointment = Appointment.query.get_or_404(appointment_id)
        patient = Patient.query.get_or_404(appointment.patient_id)

        visit = Visit.query.filter_by(appointment_id=appointment_id).first()

        if not visit or not visit.accession_number:
            return jsonify(
                {"success": False, "error": "No DICOM study found for this appointment"}
            ), 404

        study_images = (
            DicomImage.query.filter_by(accession_number=visit.accession_number)
            .order_by(DicomImage.series_instance_uid, DicomImage.instance_number)
            .all()
        )

        if not study_images:
            return jsonify(
                {
                    "success": False,
                    "error": "No DICOM images found for this appointment",
                }
            ), 404

        dicom_patient_ids = set()
        for img in study_images:
            if img.patient_id:
                dicom_patient_ids.add(str(img.patient_id))

        appointment_patient_id = str(patient.patient_id)

        patient_link_verified = (
            not dicom_patient_ids or appointment_patient_id in dicom_patient_ids
        )

        if dicom_patient_ids and not patient_link_verified:
            logger.error(
                f"PATIENT MISMATCH: DICOM images patient_ids={dicom_patient_ids} "
                f"do not match appointment patient_id={appointment_patient_id}"
            )
            return jsonify(
                {
                    "success": False,
                    "error": "Data integrity error: images belong to different patient",
                }
            ), 500

        images_data = []
        for img in study_images:
            images_data.append(
                {
                    "id": img.id,
                    "sop_instance_uid": img.sop_instance_uid,
                    "series_instance_uid": img.series_instance_uid,
                    "series_number": img.series_number,
                    "series_description": img.series_description,
                    "instance_number": img.instance_number,
                    "modality": img.modality,
                    "thumbnail_url": f"/api/dicom/images/{img.id}/thumbnail"
                    if img.thumbnail_path
                    else None,
                    "file_url": f"/api/dicom/images/{img.id}/file",
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "appointment": {
                        "id": appointment.id,
                        "date": appointment.date.isoformat()
                        if appointment.date
                        else None,
                        "time": appointment.time,
                        "status": appointment.status,
                        "patient_id": patient.patient_id,
                    },
                    "patient": {
                        "id": patient.id,
                        "patient_id": patient.patient_id,
                        "name": f"{patient.first_name} {patient.last_name}",
                    },
                    "visit": {
                        "id": visit.id,
                        "visit_status": visit.visit_status,
                        "exam_type": visit.exam_type,
                        "accession_number": visit.accession_number,
                    },
                    "study": {
                        "study_instance_uid": study_images[0].study_instance_uid,
                        "study_date": study_images[0].study_date.isoformat()
                        if study_images[0].study_date
                        else None,
                        "study_description": study_images[0].study_description,
                        "modality": study_images[0].modality,
                    },
                    "images": images_data,
                    "_meta": {
                        "total_images": len(images_data),
                        "patient_link_verified": patient_link_verified,
                    },
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting images by appointment: {e}", exc_info=True)
        error_msg = "Failed to get images" if not current_app.debug else str(e)
        return jsonify({"success": False, "error": error_msg}), 500

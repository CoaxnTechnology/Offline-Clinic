"""
Reporting API Routes
Handles PDF report generation, listing, downloading, and management
"""
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import DicomImage, Patient
from app.utils.decorators import require_role
from app.services.report_service import (
    create_report,
    generate_report_pdf,
    get_report_by_id,
    get_report_by_number,
    list_reports,
    delete_report
)
import os
import logging

logger = logging.getLogger(__name__)

reporting_bp = Blueprint('reporting', __name__, url_prefix='/api/reports')


@reporting_bp.route('', methods=['GET'])
@jwt_required()
def list_reports_endpoint():
    """
    List reports with pagination and filters
    
    Query params:
        patient_id: Filter by patient ID
        study_instance_uid: Filter by study UID
        status: Filter by status (completed, generating, failed)
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
    """
    try:
        # Validate pagination
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
        if limit > 100:
            limit = 100
        
        # Get filters
        patient_id = request.args.get('patient_id')
        study_instance_uid = request.args.get('study_instance_uid')
        status = request.args.get('status')
        
        # Validate filters
        if patient_id and len(patient_id) > 20:
            return jsonify({
                'success': False,
                'error': 'Invalid patient_id format'
            }), 400
        
        if study_instance_uid and len(study_instance_uid) > 255:
            return jsonify({
                'success': False,
                'error': 'Invalid study_instance_uid format'
            }), 400
        
        if status and status not in ['completed', 'generating', 'failed']:
            return jsonify({
                'success': False,
                'error': 'Invalid status. Must be: completed, generating, or failed'
            }), 400
        
        # Get reports
        result = list_reports(
            patient_id=patient_id,
            study_instance_uid=study_instance_uid,
            status=status,
            page=page,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        logger.error(f"Error listing reports: {e}", exc_info=True)
        error_msg = 'Failed to list reports' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@reporting_bp.route('/generate', methods=['POST'])
@jwt_required()
@require_role('doctor', 'receptionist')
def generate_report():
    from app.models import Admin
    # Get current user from JWT
    user_id = int(get_jwt_identity())
    current_user = Admin.query.get(user_id)
    """
    Generate PDF report for a DICOM study
    
    Body:
        study_instance_uid: Study Instance UID (required)
        patient_id: Patient ID (optional)
        report_number: Custom report number (optional)
        notes: Additional notes (optional)
        async: Generate asynchronously via Celery (default: false)
    """
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        study_instance_uid = data.get('study_instance_uid')
        if not study_instance_uid:
            return jsonify({
                'success': False,
                'error': 'study_instance_uid is required'
            }), 400
        
        if len(study_instance_uid) > 255:
            return jsonify({
                'success': False,
                'error': 'Invalid study_instance_uid format'
            }), 400
        
        # Check if study exists
        study_images = DicomImage.query.filter_by(study_instance_uid=study_instance_uid).first()
        if not study_images:
            return jsonify({
                'success': False,
                'error': 'Study not found'
            }), 404
        
        # Get optional fields
        patient_id = data.get('patient_id')
        report_number = data.get('report_number')
        notes = data.get('notes')
        async_generation = data.get('async', False)
        
        # Create report record
        report = create_report(
            study_instance_uid=study_instance_uid,
            patient_id=patient_id,
            generated_by=current_user.id,
            report_number=report_number,
            notes=notes
        )
        
        db.session.commit()
        
        # Generate PDF
        if async_generation:
            # Use Celery for async generation
            try:
                from tasks.report_tasks import generate_pdf_report_task
                task = generate_pdf_report_task.delay(study_instance_uid, report.id)
                report.generation_task_id = task.id
                report.status = 'generating'
                db.session.commit()
                
                logger.info(f"Report generation queued: Report ID {report.id}, Task ID {task.id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Report generation started',
                    'data': {
                        'report_id': report.id,
                        'report_number': report.report_number,
                        'status': 'generating',
                        'task_id': task.id,
                        'study_instance_uid': study_instance_uid
                    }
                }), 202  # Accepted
            except ImportError:
                logger.warning("Celery not available, generating synchronously")
                # Fall through to sync generation
        
        # Synchronous generation
        try:
            pdf_path = generate_report_pdf(report)
            
            return jsonify({
                'success': True,
                'message': 'Report generated successfully',
                'data': report.to_dict()
            }), 201
        except Exception as e:
            report.status = 'failed'
            db.session.commit()
            logger.error(f"Failed to generate report PDF: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'Failed to generate PDF: {str(e)}',
                'data': {
                    'report_id': report.id,
                    'status': 'failed'
                }
            }), 500
    
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        db.session.rollback()
        error_msg = 'Failed to generate report' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@reporting_bp.route('/<int:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    """Get report details by ID"""
    try:
        report = get_report_by_id(report_id)
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': report.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error getting report {report_id}: {e}", exc_info=True)
        error_msg = 'Failed to get report' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@reporting_bp.route('/number/<report_number>', methods=['GET'])
@jwt_required()
def get_report_by_number_endpoint(report_number):
    """Get report details by report number"""
    try:
        report = get_report_by_number(report_number)
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': report.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error getting report {report_number}: {e}", exc_info=True)
        error_msg = 'Failed to get report' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@reporting_bp.route('/<int:report_id>/download', methods=['GET'])
@jwt_required()
def download_report(report_id):
    """Download PDF report file"""
    try:
        report = get_report_by_id(report_id)
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        if report.status != 'completed':
            return jsonify({
                'success': False,
                'error': f'Report is not ready. Status: {report.status}'
            }), 400
        
        if not report.file_path or not os.path.exists(report.file_path):
            return jsonify({
                'success': False,
                'error': 'Report file not found'
            }), 404
        
        # Validate file path (security)
        file_path = os.path.abspath(report.file_path)
        reports_dir = os.path.abspath(current_app.config.get('PDF_REPORTS_PATH', 'reports'))
        if not file_path.startswith(reports_dir):
            logger.warning(f"Invalid file path attempt: {report.file_path}")
            return jsonify({
                'success': False,
                'error': 'Invalid file path'
            }), 400
        
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{report.report_number}.pdf"
        )
    
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {e}", exc_info=True)
        error_msg = 'Failed to download report' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@reporting_bp.route('/<int:report_id>/status', methods=['GET'])
@jwt_required()
def get_report_status(report_id):
    """Get report generation status"""
    try:
        report = get_report_by_id(report_id)
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        status_data = {
            'report_id': report.id,
            'report_number': report.report_number,
            'status': report.status,
            'created_at': report.created_at.isoformat() if report.created_at else None
        }
        
        # If async generation, check Celery task status
        if report.generation_task_id:
            try:
                from celery.result import AsyncResult
                from app.extensions import celery
                task_result = AsyncResult(report.generation_task_id, app=celery)
                status_data['task_status'] = task_result.state
                if task_result.state == 'PROCESSING':
                    status_data['task_progress'] = task_result.info
            except ImportError:
                pass
        
        return jsonify({
            'success': True,
            'data': status_data
        })
    
    except Exception as e:
        logger.error(f"Error getting report status {report_id}: {e}", exc_info=True)
        error_msg = 'Failed to get report status' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@reporting_bp.route('/<int:report_id>', methods=['DELETE'])
@jwt_required()
@require_role('doctor', 'receptionist')
def delete_report_endpoint(report_id):
    """Delete a report and its PDF file"""
    try:
        success = delete_report(report_id)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Report deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}", exc_info=True)
        db.session.rollback()
        error_msg = 'Failed to delete report' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

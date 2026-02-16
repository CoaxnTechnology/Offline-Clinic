"""
Reporting API Routes
Handles PDF report generation, listing, downloading, and management
"""
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import DicomImage, Patient
from app.utils.decorators import require_role, get_current_clinic_id, verify_clinic_access
from app.utils.audit import log_audit
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
        
        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()

        # Get reports
        result = list_reports(
            patient_id=patient_id,
            study_instance_uid=study_instance_uid,
            status=status,
            page=page,
            limit=limit,
            clinic_id=clinic_id if not is_super else None
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
        from app.models import Visit, ReportTemplate
        patient_id = data.get('patient_id')
        report_number = data.get('report_number')
        notes = data.get('notes')
        template_id = data.get('template_id')
        template_data = data.get('template_data')  # JSON object with field values
        language = data.get('language', 'en')
        visit_id = data.get('visit_id')
        async_generation = data.get('async', False)
        
        # Validate template if provided
        template = None
        if template_id:
            template = ReportTemplate.query.get(template_id)
            if not template:
                return jsonify({
                    'success': False,
                    'error': 'Template not found'
                }), 404
            
            if not template.is_active:
                return jsonify({
                    'success': False,
                    'error': 'Template is not active'
                }), 400
            
            # Validate template_data structure
            if not template_data or not isinstance(template_data, dict):
                return jsonify({
                    'success': False,
                    'error': 'template_data must be a JSON object with field values'
                }), 400
        
        # Find Visit if visit_id provided, or try to find by study_instance_uid
        visit = None
        if visit_id:
            visit = Visit.query.get(visit_id)
        else:
            # Try to find Visit by study_instance_uid via DICOM images
            if study_images:
                visit = Visit.query.filter_by(study_instance_uid=study_images.study_instance_uid).first()
        
        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()

        # Create report record
        report = create_report(
            study_instance_uid=study_instance_uid,
            patient_id=patient_id,
            generated_by=current_user.id,
            report_number=report_number,
            notes=notes,
            template_id=template_id,
            template_data=template_data,
            language=language,
            visit_id=visit.id if visit else None,
            clinic_id=clinic_id
        )
        
        db.session.commit()
        
        # Audit log
        log_audit('report', 'create', user_id=current_user.id, entity_id=str(report.id), details={'report_number': report.report_number, 'study_instance_uid': study_instance_uid, 'template_id': template_id})
        
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
            
            # Audit log for PDF generation
            log_audit('report', 'export', user_id=current_user.id, entity_id=str(report.id), details={'report_number': report.report_number, 'pdf_path': pdf_path})
            
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

        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()
        denied = verify_clinic_access(report, clinic_id, is_super)
        if denied:
            return denied

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

        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()
        denied = verify_clinic_access(report, clinic_id, is_super)
        if denied:
            return denied

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

        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()
        denied = verify_clinic_access(report, clinic_id, is_super)
        if denied:
            return denied

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
        
        # Audit log for report download/export
        user_id = int(get_jwt_identity())
        log_audit('report', 'export', user_id=user_id, entity_id=str(report_id), details={'report_number': report.report_number, 'download': True})
        
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

        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()
        denied = verify_clinic_access(report, clinic_id, is_super)
        if denied:
            return denied

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
    """Delete a report and its PDF file. PDF spec §6: only draft reports can be deleted."""
    from app.models import Report
    try:
        report = Report.query.get(report_id)
        if not report:
            return jsonify({'success': False, 'error': 'Report not found'}), 404

        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()
        denied = verify_clinic_access(report, clinic_id, is_super)
        if denied:
            return denied

        if report.lifecycle_state in ('validated', 'archived'):
            return jsonify({
                'success': False,
                'error': 'Report is validated or archived and cannot be deleted (PDF spec §6)'
            }), 403
        success = delete_report(report_id)
        if not success:
            return jsonify({'success': False, 'error': 'Report not found'}), 404
        return jsonify({'success': True, 'message': 'Report deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}", exc_info=True)
        db.session.rollback()
        error_msg = 'Failed to delete report' if not current_app.debug else str(e)
        return jsonify({'success': False, 'error': error_msg}), 500


@reporting_bp.route('/<int:report_id>/validate', methods=['POST'])
@jwt_required()
@require_role('doctor')
def validate_report_endpoint(report_id):
    """
    Validate a report (PDF spec §6: Draft → Validated; no modification after).
    Enforces mandatory fields if template is used.
    """
    from app.models import Report, ReportTemplate
    from app.services.report_service import validate_report
    import json
    try:
        user_id = int(get_jwt_identity())
        report = Report.query.get(report_id)
        if not report:
            return jsonify({'success': False, 'error': 'Report not found'}), 404

        # Clinic isolation
        clinic_id, is_super = get_current_clinic_id()
        denied = verify_clinic_access(report, clinic_id, is_super)
        if denied:
            return denied

        # Check if report is already validated/archived
        if report.lifecycle_state not in (None, 'draft'):
            return jsonify({
                'success': False,
                'error': 'Report is already validated or archived'
            }), 400
        
        # If template is used, validate mandatory fields
        if report.template_id:
            template = ReportTemplate.query.get(report.template_id)
            if template:
                required_fields = template.get_required_fields()
                template_data = json.loads(report.template_data) if report.template_data else {}
                
                missing_fields = []
                for field_code in required_fields:
                    if field_code not in template_data or not template_data[field_code]:
                        missing_fields.append(field_code)
                
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required fields: {", ".join(missing_fields)}',
                        'missing_fields': missing_fields
                    }), 400
        
        # Validate the report
        validated_report = validate_report(report_id, user_id)
        if not validated_report:
            return jsonify({
                'success': False,
                'error': 'Failed to validate report'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Report validated',
            'data': validated_report.to_dict()
        })
    except Exception as e:
        logger.error(f"Error validating report {report_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

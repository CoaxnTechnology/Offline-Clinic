"""
Celery tasks for report generation
"""
import os
import logging
from celery import current_task
from app.extensions import celery, db
from app.models import DicomImage, Patient
try:
    from app.utils.pdf_utils import generate_pdf_report
except ImportError:
    # Fallback if pdf_utils doesn't exist
    def generate_pdf_report(*args, **kwargs):
        return None

logger = logging.getLogger(__name__)


@celery.task(bind=True, name='tasks.generate_pdf_report')
def generate_pdf_report_task(self, study_instance_uid, output_path=None):
    """
    Generate PDF report for a DICOM study
    
    Args:
        study_instance_uid: Study Instance UID
        output_path: Optional output path for PDF
    
    Returns:
        dict: Report generation result
    """
    try:
        with db.session.begin():
            # Get all images for this study
            images = DicomImage.query.filter_by(
                study_instance_uid=study_instance_uid
            ).all()
            
            if not images:
                return {'success': False, 'error': 'No images found for study'}
            
            # Get patient info
            patient = Patient.query.get(images[0].patient_id) if images[0].patient_id else None
            
            self.update_state(state='PROCESSING', meta={'step': 'Generating PDF report'})
            
            # Generate PDF
            pdf_path = generate_pdf_report(
                study_instance_uid=study_instance_uid,
                patient=patient,
                images=images,
                output_path=output_path
            )
            
            return {
                'success': True,
                'study_instance_uid': study_instance_uid,
                'pdf_path': pdf_path,
                'image_count': len(images)
            }
    
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


@celery.task(name='tasks.batch_generate_reports')
def batch_generate_reports(study_instance_uids):
    """
    Generate PDF reports for multiple studies
    
    Args:
        study_instance_uids: List of Study Instance UIDs
    
    Returns:
        dict: Task results
    """
    results = []
    for study_uid in study_instance_uids:
        result = generate_pdf_report_task.delay(study_uid)
        results.append({'study_uid': study_uid, 'task_id': result.id})
    
    return {
        'success': True,
        'total': len(study_instance_uids),
        'tasks': results
    }

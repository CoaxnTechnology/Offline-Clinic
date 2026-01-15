"""
Celery tasks for data synchronization and maintenance
"""
import logging
from datetime import datetime, timedelta
from app.extensions import celery, db
from app.models import DicomImage, Appointment, Patient

logger = logging.getLogger(__name__)


@celery.task(name='tasks.update_appointment_statuses')
def update_appointment_statuses():
    """
    Update appointment statuses based on DICOM image reception
    If images are received for an appointment, update status to 'In-Scan' or 'Review'
    
    Returns:
        dict: Update results
    """
    try:
        updated_count = 0
        
        # Find appointments with status 'Waiting' or 'In-Room' that have DICOM images
        appointments = Appointment.query.filter(
            Appointment.status.in_(['Waiting', 'In-Room'])
        ).all()
        
        for appointment in appointments:
            # Check if there are DICOM images for this patient today
            today = datetime.now().date()
            images_today = DicomImage.query.filter_by(
                patient_id=appointment.patient_id,
                study_date=today
            ).count()
            
            if images_today > 0:
                # Update status based on image count
                if images_today >= 3:
                    appointment.status = 'Review'
                else:
                    appointment.status = 'In-Scan'
                
                updated_count += 1
        
        db.session.commit()
        
        return {
            'success': True,
            'updated_count': updated_count,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error updating appointment statuses: {e}", exc_info=True)
        db.session.rollback()
        return {'success': False, 'error': str(e)}


@celery.task(name='tasks.sync_patient_data')
def sync_patient_data(patient_id):
    """
    Sync patient data from DICOM images to patient record
    
    Args:
        patient_id: Patient ID
    
    Returns:
        dict: Sync results
    """
    try:
        patient = Patient.query.get(patient_id)
        if not patient:
            return {'success': False, 'error': 'Patient not found'}
        
        # Get latest DICOM image for this patient
        latest_image = DicomImage.query.filter_by(
            patient_id=patient_id
        ).order_by(DicomImage.study_date.desc()).first()
        
        if latest_image:
            # Update patient info if missing
            if not patient.birth_date and latest_image.patient_birth_date:
                patient.birth_date = latest_image.patient_birth_date
            
            if not patient.gender and latest_image.patient_sex:
                patient.gender = latest_image.patient_sex
            
            db.session.commit()
        
        return {
            'success': True,
            'patient_id': patient_id,
            'updated': latest_image is not None
        }
    
    except Exception as e:
        logger.error(f"Error syncing patient data: {e}", exc_info=True)
        db.session.rollback()
        return {'success': False, 'error': str(e)}


@celery.task(name='tasks.daily_maintenance')
def daily_maintenance():
    """
    Daily maintenance tasks: cleanup, sync, reports
    
    Returns:
        dict: Maintenance results
    """
    results = {}
    
    # Update appointment statuses
    results['appointment_statuses'] = update_appointment_statuses()
    
    # Cleanup old files (older than 90 days)
    from tasks.dicom_tasks import cleanup_old_dicom_files
    results['cleanup'] = cleanup_old_dicom_files.delay(90).get()
    
    return {
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'results': results
    }

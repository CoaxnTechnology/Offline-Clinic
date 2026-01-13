"""
Celery tasks for DICOM processing
"""
import os
import logging
from celery import current_task
from app.extensions import celery, db
from app.models import DicomImage, DicomMeasurement
from app.utils.dicom_utils import generate_thumbnail, save_thumbnail_file
from pydicom import dcmread

logger = logging.getLogger(__name__)


@celery.task(bind=True, name='tasks.process_dicom_image')
def process_dicom_image(self, dicom_image_id):
    """
    Process DICOM image: generate thumbnail, extract metadata
    
    Args:
        dicom_image_id: ID of DicomImage record
    
    Returns:
        dict: Processing result
    """
    try:
        with db.session.begin():
            image = DicomImage.query.get(dicom_image_id)
            if not image:
                return {'success': False, 'error': 'Image not found'}
            
            # Update task state
            self.update_state(state='PROCESSING', meta={'step': 'Reading DICOM file'})
            
            # Read DICOM file
            if not os.path.exists(image.file_path):
                return {'success': False, 'error': 'DICOM file not found'}
            
            ds = dcmread(image.file_path)
            
            # Generate thumbnail if not exists
            if not image.thumbnail_path or not os.path.exists(image.thumbnail_path):
                self.update_state(state='PROCESSING', meta={'step': 'Generating thumbnail'})
                thumbnail_path = save_thumbnail_file(
                    ds,
                    os.path.dirname(image.thumbnail_path) if image.thumbnail_path else 'thumbnails',
                    image.sop_instance_uid
                )
                if thumbnail_path:
                    image.thumbnail_path = thumbnail_path
            
            # Update image metadata if needed
            self.update_state(state='PROCESSING', meta={'step': 'Updating metadata'})
            db.session.commit()
            
            return {
                'success': True,
                'image_id': dicom_image_id,
                'thumbnail_path': image.thumbnail_path
            }
    
    except Exception as e:
        logger.error(f"Error processing DICOM image {dicom_image_id}: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


@celery.task(name='tasks.batch_process_dicom_images')
def batch_process_dicom_images(image_ids):
    """
    Process multiple DICOM images in batch
    
    Args:
        image_ids: List of DicomImage IDs
    
    Returns:
        dict: Processing results
    """
    results = []
    for image_id in image_ids:
        result = process_dicom_image.delay(image_id)
        results.append({'image_id': image_id, 'task_id': result.id})
    
    return {
        'success': True,
        'total': len(image_ids),
        'tasks': results
    }


@celery.task(name='tasks.cleanup_old_dicom_files')
def cleanup_old_dicom_files(days_old=90):
    """
    Cleanup old DICOM files that are older than specified days
    
    Args:
        days_old: Number of days to keep files (default: 90)
    
    Returns:
        dict: Cleanup results
    """
    try:
        from datetime import datetime, timedelta
        from app.config import Config
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Find old images
        old_images = DicomImage.query.filter(
            DicomImage.created_at < cutoff_date
        ).all()
        
        deleted_count = 0
        error_count = 0
        
        for image in old_images:
            try:
                # Delete file
                if os.path.exists(image.file_path):
                    os.remove(image.file_path)
                
                # Delete thumbnail
                if image.thumbnail_path and os.path.exists(image.thumbnail_path):
                    os.remove(image.thumbnail_path)
                
                # Delete database record
                db.session.delete(image)
                deleted_count += 1
            
            except Exception as e:
                logger.error(f"Error deleting image {image.id}: {e}")
                error_count += 1
        
        db.session.commit()
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'error_count': error_count,
            'cutoff_date': cutoff_date.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}

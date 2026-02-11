"""
DICOM Utilities for thumbnail generation, DICOM parsing, and file handling
"""
import os
import io
import base64
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import numpy as np
from PIL import Image
from pydicom import Dataset
from pydicom.uid import generate_uid

# Use dedicated DICOM logger for all DICOM-related operations
logger = logging.getLogger("dicom")


def generate_thumbnail(ds: Dataset, max_size: tuple = (200, 200)) -> Optional[str]:
    """
    Generate thumbnail from DICOM dataset pixel data
    
    Args:
        ds: Pydicom Dataset
        max_size: Maximum thumbnail size (width, height)
    
    Returns:
        Base64 encoded JPEG thumbnail string or None
    """
    try:
        # Handle compressed data (JPEG Baseline from Samsung, etc.)
        if hasattr(ds, 'file_meta') and ds.file_meta and hasattr(ds.file_meta, 'TransferSyntaxUID'):
            if ds.file_meta.TransferSyntaxUID.is_compressed:
                ds.decompress()  # Decompress to raw pixel data
        
        if not hasattr(ds, 'pixel_array'):
            logger.warning("Dataset does not have pixel_array")
            return None
        
        pixel_data = ds.pixel_array
        
        # Handle multiframe (cine loops) - take first frame
        if pixel_data.ndim >= 3:
            if pixel_data.shape[0] > 1:  # Multiframe
                pixel_data = pixel_data[0]
            if pixel_data.ndim == 3 and pixel_data.shape[-1] == 3:  # RGB
                pixel_data = np.mean(pixel_data, axis=-1)
        
        # Normalize to 8-bit
        p_min, p_max = pixel_data.min(), pixel_data.max()
        if p_max > p_min:
            pixel_data = np.uint8(255 * (pixel_data - p_min) / (p_max - p_min))
        else:
            pixel_data = np.uint8(pixel_data)
        
        # Convert to PIL Image
        img = Image.fromarray(pixel_data).convert('RGB')
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to base64
        bio = io.BytesIO()
        img.save(bio, 'JPEG', quality=85)
        base64_str = base64.b64encode(bio.getvalue()).decode()
        
        return base64_str
    
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}", exc_info=True)
        return None


def save_thumbnail_file(ds: Dataset, storage_path: str, sop_instance_uid: str) -> Optional[str]:
    """
    Save thumbnail to file system - Production ready
    
    Args:
        ds: Pydicom Dataset
        storage_path: Directory to save thumbnail
        sop_instance_uid: SOP Instance UID for filename
    
    Returns:
        Path to saved thumbnail file or None
    """
    try:
        # Production: Create directory with proper permissions
        os.makedirs(storage_path, exist_ok=True, mode=0o755)
        
        thumbnail_base64 = generate_thumbnail(ds)
        if not thumbnail_base64:
            logger.warning(f"Failed to generate thumbnail for {sop_instance_uid}")
            return None
        
        # Production: Sanitize filename
        safe_uid = sop_instance_uid.replace('/', '_').replace('\\', '_')
        thumbnail_path = os.path.join(storage_path, f"{safe_uid}.jpg")
        thumbnail_path = os.path.abspath(thumbnail_path)
        
        # Production: Validate path is within storage directory
        if not thumbnail_path.startswith(os.path.abspath(storage_path)):
            logger.error(f"Invalid thumbnail path: {thumbnail_path}")
            return None
        
        # Decode and save
        thumbnail_data = base64.b64decode(thumbnail_base64)
        
        # Production: Check file size (max 5MB for thumbnails)
        if len(thumbnail_data) > 5 * 1024 * 1024:
            logger.warning(f"Thumbnail too large: {len(thumbnail_data)} bytes")
            return None
        
        with open(thumbnail_path, 'wb') as f:
            f.write(thumbnail_data)
        
        logger.debug(f"Saved thumbnail: {thumbnail_path}")
        return thumbnail_path
    
    except Exception as e:
        logger.error(f"Failed to save thumbnail: {e}", exc_info=True)
        return None


def extract_dicom_metadata(ds: Dataset) -> Dict[str, Any]:
    """
    Extract metadata from DICOM dataset
    
    Args:
        ds: Pydicom Dataset
    
    Returns:
        Dictionary of extracted metadata
    """
    metadata = {}
    
    # Patient Information
    metadata['patient_name'] = str(getattr(ds, 'PatientName', ''))
    metadata['patient_id'] = str(getattr(ds, 'PatientID', ''))
    metadata['patient_birth_date'] = getattr(ds, 'PatientBirthDate', None)
    metadata['patient_sex'] = getattr(ds, 'PatientSex', '')
    
    # Study Information
    metadata['study_instance_uid'] = str(getattr(ds, 'StudyInstanceUID', ''))
    metadata['study_date'] = getattr(ds, 'StudyDate', None)
    metadata['study_time'] = str(getattr(ds, 'StudyTime', ''))
    metadata['study_description'] = str(getattr(ds, 'StudyDescription', ''))
    metadata['accession_number'] = str(getattr(ds, 'AccessionNumber', ''))
    metadata['referring_physician'] = str(getattr(ds, 'ReferringPhysicianName', ''))
    metadata['institution_name'] = str(getattr(ds, 'InstitutionName', ''))
    
    # Series Information
    metadata['series_instance_uid'] = str(getattr(ds, 'SeriesInstanceUID', ''))
    metadata['series_number'] = getattr(ds, 'SeriesNumber', None)
    metadata['series_description'] = str(getattr(ds, 'SeriesDescription', ''))
    metadata['modality'] = str(getattr(ds, 'Modality', ''))
    metadata['body_part_examined'] = str(getattr(ds, 'BodyPartExamined', ''))
    metadata['series_date'] = getattr(ds, 'SeriesDate', None)
    metadata['series_time'] = str(getattr(ds, 'SeriesTime', ''))
    
    # Image Information
    metadata['sop_instance_uid'] = str(getattr(ds, 'SOPInstanceUID', ''))
    metadata['instance_number'] = getattr(ds, 'InstanceNumber', None)
    metadata['manufacturer'] = str(getattr(ds, 'Manufacturer', ''))
    metadata['manufacturer_model_name'] = str(getattr(ds, 'ManufacturerModelName', ''))
    
    return metadata


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse DICOM date string (YYYYMMDD) to datetime.date
    
    Args:
        date_str: DICOM date string
    
    Returns:
        datetime.date object or None
    """
    if not date_str or len(date_str) < 8:
        return None
    
    try:
        return datetime.strptime(date_str[:8], '%Y%m%d').date()
    except (ValueError, TypeError):
        return None


def save_dicom_file(ds: Dataset, storage_path: str, sop_instance_uid: str) -> str:
    """
    Save DICOM dataset to file system - Production ready
    
    Args:
        ds: Pydicom Dataset
        storage_path: Directory to save DICOM file
        sop_instance_uid: SOP Instance UID for filename
    
    Returns:
        Path to saved DICOM file
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Create storage directory with proper permissions
    try:
        os.makedirs(storage_path, exist_ok=True, mode=0o755)
    except OSError as e:
        logger.error(f"Failed to create storage directory {storage_path}: {e}")
        raise
    
    # Organize by study date if available
    study_date = getattr(ds, 'StudyDate', None)
    if study_date and len(str(study_date)) >= 8:
        date_folder = str(study_date)[:8]  # YYYYMMDD
        file_dir = os.path.join(storage_path, date_folder)
        try:
            os.makedirs(file_dir, exist_ok=True, mode=0o755)
        except OSError as e:
            logger.error(f"Failed to create date directory {file_dir}: {e}")
            file_dir = storage_path  # Fallback to base directory
    else:
        file_dir = storage_path
    
    # Sanitize filename to prevent path traversal
    safe_uid = sop_instance_uid.replace('/', '_').replace('\\', '_')
    file_path = os.path.join(file_dir, f"{safe_uid}.dcm")
    
    # Ensure absolute path for security
    file_path = os.path.abspath(file_path)
    
    try:
        ds.save_as(file_path, write_like_original=False)
        logger.info(f"Saved DICOM file: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save DICOM file {file_path}: {e}", exc_info=True)
        raise


def create_mwl_dataset(
    patient_id: str,
    patient_name: str,
    patient_sex: str,
    accession_number: str,
    study_description: str,
    scheduled_date: str,
    scheduled_time: str,
    modality: str = "US",
    patient_birth_date: str = "",
    requested_procedure_id: str = "",
    scheduled_procedure_step_id: str = "",
) -> Dataset:
    """
    Create Modality Worklist (MWL) dataset per PDF spec §4.
    Required: PatientName, PatientID, PatientBirthDate, PatientSex, AccessionNumber,
    RequestedProcedureID, ScheduledProcedureStepID, StudyDescription.
    """
    ds = Dataset()

    # Patient Information (mandatory MWL fields)
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.PatientBirthDate = patient_birth_date[:8] if patient_birth_date and len(patient_birth_date) >= 8 else (patient_birth_date or "")
    ds.PatientSex = patient_sex
    ds.AccessionNumber = accession_number
    ds.RequestedProcedureDescription = study_description
    ds.StudyInstanceUID = generate_uid()
    if requested_procedure_id:
        ds.RequestedProcedureID = requested_procedure_id

    # Scheduled Procedure Step Sequence
    ds.ScheduledProcedureStepSequence = [Dataset()]
    sps_item = ds.ScheduledProcedureStepSequence[0]
    sps_item.ScheduledProcedureStepDescription = study_description
    sps_item.ScheduledProcedureStepStartDate = scheduled_date[:8] if len(scheduled_date) >= 8 else scheduled_date
    sps_item.ScheduledProcedureStepStartTime = scheduled_time if len(scheduled_time) >= 4 else "0900"
    sps_item.Modality = modality
    # Many devices filter on ScheduledProcedureStepStatus and expect 'SCHEDULED'
    sps_item.ScheduledProcedureStepStatus = "SCHEDULED"
    sps_item.ScheduledPerformingPhysicianName = ""
    if scheduled_procedure_step_id:
        sps_item.ScheduledProcedureStepID = scheduled_procedure_step_id

    return ds

"""
DICOM Service for handling MWL queries, C-STORE operations, and DICOM data management
"""
import os
import logging
import threading
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from pynetdicom import AE, evt, debug_logger
from pynetdicom.sop_class import Verification
from pynetdicom.dsutils import encode
from pydicom import Dataset
from pydicom.uid import (
    generate_uid,
    ImplicitVRLittleEndian,
    ExplicitVRLittleEndian,
    JPEGBaseline8Bit
)

from app.extensions import db
from app.config import Config
from app.models import (
    Patient, Appointment, DicomImage, DicomMeasurement
)
from app.utils.dicom_utils import (
    extract_dicom_metadata, save_dicom_file, save_thumbnail_file,
    parse_date, create_mwl_dataset
)
import json

logger = logging.getLogger(__name__)

# Global variables for DICOM servers
_mwl_server_thread = None
_storage_server_thread = None
_mpps_server_thread = None
_mwl_server_running = False
_storage_server_running = False
_mpps_server_running = False


def handle_mwl_find(event):
    """
    Handle C-FIND request for Modality Worklist
    
    This function is called when a DICOM device queries for worklist items
    Production-ready with logging and validation
    """
    identifier = event.identifier
    if identifier is None:
        logger.warning("MWL query received with no identifier")
        yield 0xC000, None
        return

    # Extract query parameters
    query_date = getattr(identifier, 'ScheduledProcedureStepStartDate', None)
    modality = None
    
    if hasattr(identifier, 'ScheduledProcedureStepSequence') and len(identifier.ScheduledProcedureStepSequence) > 0:
        sps = identifier.ScheduledProcedureStepSequence[0]
        modality = getattr(sps, 'Modality', None)
    
    # Production: Log MWL query
    caller_ae = event.assoc.requestor.ae_title if hasattr(event, 'assoc') else 'unknown'
    logger.info(f"MWL query from {caller_ae} - Date: {query_date}, Modality: {modality}")

    try:
        # Query appointments published to MWL (have accession_number) and not deleted
        query = Appointment.query.filter(
            Appointment.status.in_(['Waiting', 'With Doctor', 'With Technician', 'Completed']),
            Appointment.accession_number.isnot(None),
            Appointment.deleted_at.is_(None),
        )
        
        # Filter by date if provided
        if query_date:
            query_date_str = str(query_date)
            if len(query_date_str) >= 8:
                try:
                    appt_date = datetime.strptime(query_date_str[:8], '%Y%m%d').date()
                    query = query.filter(Appointment.date == appt_date)
                except ValueError:
                    pass
        
        appointments = query.all()
        
        # Filter by modality if provided
        if modality and modality != 'US':
            # For now, only return US (Ultrasound) studies
            appointments = []
        
        # Generate MWL datasets for each appointment (PDF spec §4)
        for appointment in appointments:
            patient = Patient.query.get(appointment.patient_id)
            if not patient or patient.deleted_at:
                continue
            birth_str = patient.birth_date.strftime('%Y%m%d') if getattr(patient, 'birth_date', None) and patient.birth_date else ''
            ds = create_mwl_dataset(
                patient_id=patient.id,
                patient_name=f"{patient.first_name} {patient.last_name}",
                patient_sex=(patient.gender or 'M')[:1],
                accession_number=appointment.accession_number,
                study_description='OB/GYN Ultrasound',
                scheduled_date=appointment.date.strftime('%Y%m%d'),
                scheduled_time=(appointment.time or '').replace(':', '')[:4] or '0900',
                modality='US',
                patient_birth_date=birth_str,
                requested_procedure_id=appointment.requested_procedure_id or '',
                scheduled_procedure_step_id=appointment.scheduled_procedure_step_id or '',
            )
            yield 0xFF00, ds
        
        yield 0x0000, None
    
    except Exception as e:
        logger.error(f"Error in MWL find handler: {e}", exc_info=True)
        yield 0xC000, None


def handle_store(event):
    """
    Handle C-STORE request for receiving DICOM images
    
    This function is called when a DICOM device sends an image
    Production-ready with proper error handling, validation, and logging
    """
    import time
    start_time = time.time()
    
    ds = event.dataset
    ds.file_meta = event.file_meta
    sop_uid = ds.SOPInstanceUID
    
    # Production: Validate SOP Instance UID
    if not sop_uid or len(sop_uid) > 255:
        logger.error(f"Invalid SOP Instance UID: {sop_uid}")
        return 0xC001  # Processing failure
    
    # Production: Get caller information for logging
    caller_ae = 'unknown'
    caller_ip = 'unknown'
    try:
        if hasattr(event, 'assoc') and event.assoc:
            caller_ae = getattr(event.assoc.requestor, 'ae_title', 'unknown')
            caller_ip = getattr(event.assoc.requestor, 'address', 'unknown')
    except:
        pass
    
    # Production: Check file size limit
    try:
        if hasattr(ds, 'PixelData'):
            pixel_data_size = len(ds.PixelData) if ds.PixelData else 0
            max_size = getattr(Config, 'DICOM_MAX_FILE_SIZE', 104857600)  # 100MB default
            if pixel_data_size > max_size:
                logger.warning(f"DICOM file too large: {pixel_data_size} bytes (max: {max_size}) from {caller_ae}")
                return 0xC001
    except Exception as e:
        logger.warning(f"Could not check file size: {e}")
    
    # Production: Check storage quota
    try:
        import shutil
        storage_path = Config.DICOM_STORAGE_PATH
        if os.path.exists(storage_path):
            total, used, free = shutil.disk_usage(storage_path)
            used_gb = used / (1024**3)
            quota_gb = getattr(Config, 'DICOM_STORAGE_QUOTA_GB', 100)  # 100GB default
            if used_gb >= quota_gb:
                logger.error(f"Storage quota exceeded: {used_gb:.2f}GB / {quota_gb}GB")
                return 0xC001
    except Exception as e:
        logger.warning(f"Could not check storage quota: {e}")
    
    # Production: Check for duplicate (avoid reprocessing)
    existing_image = DicomImage.query.filter_by(sop_instance_uid=sop_uid).first()
    if existing_image:
        logger.info(f"Duplicate DICOM image received: {sop_uid} (already exists)")
        return 0x0000  # Success - already stored
    
    try:
        logger.info(f"Received DICOM image: {sop_uid} from {caller_ae} ({caller_ip})")
        
        # Extract metadata
        metadata = extract_dicom_metadata(ds)
        
        # Production: Validate required metadata
        if not metadata.get('study_instance_uid') or not metadata.get('series_instance_uid'):
            logger.error(f"Missing required DICOM metadata for {sop_uid}")
            return 0xC001
        
        # Save DICOM file
        dicom_file_path = save_dicom_file(
            ds,
            Config.DICOM_STORAGE_PATH,
            sop_uid
        )
        
        # Generate and save thumbnail
        thumbnail_path = save_thumbnail_file(
            ds,
            Config.THUMBNAIL_STORAGE_PATH,
            sop_uid
        )
        
        # Find or create patient
        patient_id = metadata.get('patient_id')
        patient = None
        if patient_id:
            patient = Patient.query.get(patient_id)
        
        # Parse dates
        study_date = parse_date(metadata.get('study_date'))
        series_date = parse_date(metadata.get('series_date'))
        birth_date = parse_date(metadata.get('patient_birth_date'))
        study_instance_uid = metadata.get('study_instance_uid')
        series_instance_uid = metadata.get('series_instance_uid')
        
        # Create image record (all DICOM data in one table)
        # Note: Already checked for duplicates above, so this is a new image
        image = DicomImage(
            sop_instance_uid=sop_uid,
            study_instance_uid=study_instance_uid,
            series_instance_uid=series_instance_uid,
            patient_id=patient_id,
            patient_name=metadata.get('patient_name'),
            patient_birth_date=birth_date,
            patient_sex=metadata.get('patient_sex'),
            study_date=study_date,
            study_time=metadata.get('study_time'),
            study_description=metadata.get('study_description'),
            accession_number=metadata.get('accession_number'),
            referring_physician=metadata.get('referring_physician'),
            institution_name=metadata.get('institution_name'),
            series_number=metadata.get('series_number'),
            series_description=metadata.get('series_description'),
            series_date=series_date,
            series_time=metadata.get('series_time'),
            modality=metadata.get('modality', 'US'),
            body_part_examined=metadata.get('body_part_examined'),
            manufacturer=metadata.get('manufacturer'),
            manufacturer_model_name=metadata.get('manufacturer_model_name'),
            instance_number=metadata.get('instance_number'),
            file_path=dicom_file_path,
            thumbnail_path=thumbnail_path,
            dicom_metadata=json.dumps(metadata) if metadata else None
        )
        db.session.add(image)
        
        # Create measurement record (simplified - can be enhanced)
        if metadata.get('modality') == 'US':
            measurement = DicomMeasurement(
                dicom_image_id=image.id if image.id else None,
                patient_id=patient_id,
                study_instance_uid=study_instance_uid,
                measurement_type='Study',
                measurement_value='Received',
                measurement_data=json.dumps({'status': 'received', 'modality': 'US'})
            )
            db.session.add(measurement)
        
        db.session.commit()
        
        processing_time = time.time() - start_time
        logger.info(f"Successfully stored DICOM image: {sop_uid} for patient {patient_id} (took {processing_time:.2f}s)")
        
        # Production: Trigger background processing if Celery available
        try:
            from tasks.dicom_tasks import process_dicom_image
            if image.id:
                process_dicom_image.delay(image.id)
                logger.debug(f"Queued background processing for image {image.id}")
        except ImportError:
            logger.debug("Celery not available, skipping background processing")
        except Exception as e:
            logger.warning(f"Failed to queue background processing: {e}")
        
        return 0x0000
    
    except Exception as e:
        logger.error(f"Error storing DICOM image {sop_uid}: {e}", exc_info=True)
        db.session.rollback()
        
        # Production: Cleanup failed file if created
        try:
            if 'dicom_file_path' in locals() and os.path.exists(dicom_file_path):
                os.remove(dicom_file_path)
            if 'thumbnail_path' in locals() and thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup files: {cleanup_error}")
        
        return 0xC001  # Processing failure


def handle_mpps_create(event):
    """
    Handle MPPS N-CREATE (exam started)
    Updates Visit status to 'in_progress' and Appointment status
    """
    try:
        ds = event.request.AttributeList
        if not ds:
            logger.warning("MPPS N-CREATE received with no dataset")
            return 0xC000, None
        
        # Extract identifiers
        accession_number = getattr(ds, 'AccessionNumber', None)
        study_instance_uid = getattr(ds, 'ReferencedStudySequence', [{}])[0].get('ReferencedSOPInstanceUID', None) if hasattr(ds, 'ReferencedStudySequence') else None
        scheduled_procedure_step_id = getattr(ds, 'ScheduledProcedureStepID', None)
        
        logger.info(f"MPPS N-CREATE: Exam started - Accession: {accession_number}, StudyUID: {study_instance_uid}")
        
        # Find Visit by AccessionNumber
        from app.models import Visit
        visit = None
        if accession_number:
            visit = Visit.query.filter_by(accession_number=accession_number, deleted_at=None).first()
        
        if visit:
            visit.visit_status = 'in_progress'
            visit.study_instance_uid = study_instance_uid
            
            # Update Appointment status
            if visit.appointment:
                if visit.appointment.status == 'Waiting':
                    visit.appointment.status = 'With Technician'
            
            db.session.commit()
            logger.info(f"Updated Visit {visit.id} status to 'in_progress' via MPPS")
        else:
            logger.warning(f"MPPS N-CREATE: Visit not found for AccessionNumber: {accession_number}")
        
        # Return success
        return 0x0000, None
    
    except Exception as e:
        logger.error(f"Error handling MPPS N-CREATE: {e}", exc_info=True)
        db.session.rollback()
        return 0xC001, None


def handle_mpps_set(event):
    """
    Handle MPPS N-SET (exam status update, e.g., completed)
    Updates Visit status to 'completed' and Appointment status
    """
    try:
        ds = event.request.AttributeList
        if not ds:
            logger.warning("MPPS N-SET received with no dataset")
            return 0xC000, None
        
        # Extract identifiers
        accession_number = getattr(ds, 'AccessionNumber', None)
        procedure_step_status = getattr(ds, 'PerformedProcedureStepStatus', None)
        study_instance_uid = getattr(ds, 'ReferencedStudySequence', [{}])[0].get('ReferencedSOPInstanceUID', None) if hasattr(ds, 'ReferencedStudySequence') else None
        
        logger.info(f"MPPS N-SET: Status update - Accession: {accession_number}, Status: {procedure_step_status}")
        
        # Find Visit by AccessionNumber
        from app.models import Visit
        visit = None
        if accession_number:
            visit = Visit.query.filter_by(accession_number=accession_number, deleted_at=None).first()
        
        if visit:
            # Update Visit status based on MPPS status
            if procedure_step_status == 'COMPLETED':
                visit.visit_status = 'completed'
                visit.study_instance_uid = study_instance_uid or visit.study_instance_uid
                
                # Update Appointment status
                if visit.appointment:
                    visit.appointment.status = 'Completed'
                
                db.session.commit()
                logger.info(f"Updated Visit {visit.id} status to 'completed' via MPPS")
            elif procedure_step_status == 'DISCONTINUED':
                visit.visit_status = 'cancelled'
                db.session.commit()
                logger.info(f"Updated Visit {visit.id} status to 'cancelled' via MPPS")
        else:
            logger.warning(f"MPPS N-SET: Visit not found for AccessionNumber: {accession_number}")
        
        # Return success
        return 0x0000, None
    
    except Exception as e:
        logger.error(f"Error handling MPPS N-SET: {e}", exc_info=True)
        db.session.rollback()
        return 0xC001, None


def start_mpps_server():
    """Start the MPPS (Modality Performed Procedure Step) server"""
    global _mpps_server_thread, _mpps_server_running
    
    if _mpps_server_running:
        logger.warning("MPPS server is already running")
        return
    
    def _run_mpps_server():
        global _mpps_server_running
        try:
            ae = AE(ae_title=Config.DICOM_AE_TITLE)
            ae.require_called_aet = False
            ts = [ImplicitVRLittleEndian, ExplicitVRLittleEndian]
            
            # MPPS SOP Classes
            ae.add_supported_context('1.2.840.10008.5.1.4.32.2', ts)  # MPPS N-CREATE
            ae.add_supported_context('1.2.840.10008.5.1.4.32.3', ts)  # MPPS N-SET
            ae.add_supported_context(Verification, ts)
            
            # Production: Bind to all interfaces for remote access
            bind_address = '0.0.0.0'
            mpps_port = Config.DICOM_MWL_PORT + 2  # Use MWL port + 2 for MPPS
            logger.info(f"Starting MPPS server on {bind_address}:{mpps_port}")
            _mpps_server_running = True
            ae.start_server(
                (bind_address, mpps_port),
                block=True,
                evt_handlers=[
                    (evt.EVT_N_CREATE, handle_mpps_create),
                    (evt.EVT_N_SET, handle_mpps_set)
                ]
            )
        except OSError as e:
            if "Address already in use" in str(e):
                logger.error(f"MPPS port {mpps_port} is already in use.")
            else:
                logger.error(f"MPPS server error: {e}", exc_info=True)
            _mpps_server_running = False
        except Exception as e:
            logger.error(f"MPPS server error: {e}", exc_info=True)
            _mpps_server_running = False
    
    _mpps_server_thread = threading.Thread(target=_run_mpps_server, daemon=True, name="MPPS-Server")
    _mpps_server_thread.start()
    logger.info("MPPS server thread started")
    
    # Wait a moment to verify it started
    import time
    time.sleep(0.5)
    if not _mpps_server_running:
        logger.warning("MPPS server may not have started properly")


def start_mwl_server():
    """Start the Modality Worklist server - Production ready"""
    global _mwl_server_thread, _mwl_server_running
    
    if _mwl_server_running:
        logger.warning("MWL server is already running")
        return
    
    def _run_mwl_server():
        global _mwl_server_running
        try:
            ae = AE(ae_title=Config.DICOM_AE_TITLE)
            ae.require_called_aet = False
            ts = [ImplicitVRLittleEndian, ExplicitVRLittleEndian]
            ae.add_supported_context('1.2.840.10008.5.1.4.31', ts)  # Modality Worklist
            ae.add_supported_context(Verification, ts)
            
            # Production: Bind to all interfaces for remote access
            bind_address = '0.0.0.0'
            logger.info(f"Starting MWL server on {bind_address}:{Config.DICOM_MWL_PORT}")
            _mwl_server_running = True
            ae.start_server(
                (bind_address, Config.DICOM_MWL_PORT),
                block=True,
                evt_handlers=[(evt.EVT_C_FIND, handle_mwl_find)]
            )
        except OSError as e:
            if "Address already in use" in str(e):
                logger.error(f"Port {Config.DICOM_MWL_PORT} is already in use. Another instance may be running.")
            else:
                logger.error(f"MWL server error: {e}", exc_info=True)
            _mwl_server_running = False
        except Exception as e:
            logger.error(f"MWL server error: {e}", exc_info=True)
            _mwl_server_running = False
    
    _mwl_server_thread = threading.Thread(target=_run_mwl_server, daemon=True, name="MWL-Server")
    _mwl_server_thread.start()
    logger.info("MWL server thread started")
    
    # Wait a moment to verify it started
    import time
    time.sleep(0.5)
    if not _mwl_server_running:
        raise RuntimeError(
            "Failed to start MWL server (port %s may be in use). "
            "Set AUTO_START_DICOM=false in CI or retry after a few seconds."
            % Config.DICOM_MWL_PORT
        )


def start_storage_server():
    """Start the C-STORE server for receiving DICOM images - Production ready"""
    global _storage_server_thread, _storage_server_running
    
    if _storage_server_running:
        logger.warning("Storage server is already running")
        return
    
    def _run_storage_server():
        global _storage_server_running
        try:
            ae = AE(ae_title=Config.DICOM_AE_TITLE)
            ae.require_called_aet = False
            
            ts = [
                JPEGBaseline8Bit,
                '1.2.840.10008.1.2.4.51',  # JPEG Extended
                '1.2.840.10008.1.2.4.57',  # JPEG Lossless
                '1.2.840.10008.1.2.4.70',  # JPEG Lossless SV1
                ImplicitVRLittleEndian,
                ExplicitVRLittleEndian,
                '1.2.840.10008.1.2.2',  # Explicit VR Big Endian
            ]
            
            # Ultrasound Single-frame and Multi-frame
            ae.add_supported_context('1.2.840.10008.5.1.4.1.1.6.1', ts)  # US Single-frame
            ae.add_supported_context('1.2.840.10008.5.1.4.1.1.3.1', ts)  # US Multi-frame
            ae.add_supported_context(Verification, ts)
            
            # Production: Bind to all interfaces for remote access
            bind_address = '0.0.0.0'
            logger.info(f"Starting Storage server on {bind_address}:{Config.DICOM_STORAGE_PORT}")
            _storage_server_running = True
            ae.start_server(
                (bind_address, Config.DICOM_STORAGE_PORT),
                block=True,
                evt_handlers=[(evt.EVT_C_STORE, handle_store)]
            )
        except OSError as e:
            if "Address already in use" in str(e):
                logger.error(f"Port {Config.DICOM_STORAGE_PORT} is already in use. Another instance may be running.")
            else:
                logger.error(f"Storage server error: {e}", exc_info=True)
            _storage_server_running = False
        except Exception as e:
            logger.error(f"Storage server error: {e}", exc_info=True)
            _storage_server_running = False
    
    _storage_server_thread = threading.Thread(target=_run_storage_server, daemon=True, name="Storage-Server")
    _storage_server_thread.start()
    logger.info("Storage server thread started")
    
    # Wait a moment to verify it started
    import time
    time.sleep(0.5)
    if not _storage_server_running:
        raise RuntimeError("Failed to start Storage server")


def start_dicom_servers():
    """Start MWL, Storage, and MPPS servers"""
    start_mwl_server()
    start_storage_server()
    start_mpps_server()  # Optional but recommended


def stop_dicom_servers():
    """Stop DICOM servers (placeholder - pynetdicom doesn't have easy stop method)"""
    global _mwl_server_running, _storage_server_running, _mpps_server_running
    _mwl_server_running = False
    _storage_server_running = False
    _mpps_server_running = False
    logger.info("DICOM servers stopped")


def get_server_status() -> Dict[str, Any]:
    """Get status of DICOM servers - Production ready"""
    import socket
    
    # Check if ports are actually listening
    def check_port(port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    mwl_port_open = check_port(Config.DICOM_MWL_PORT)
    storage_port_open = check_port(Config.DICOM_STORAGE_PORT)
    mpps_port = Config.DICOM_MWL_PORT + 2
    mpps_port_open = check_port(mpps_port)
    
    return {
        'mwl_server_running': _mwl_server_running and mwl_port_open,
        'storage_server_running': _storage_server_running and storage_port_open,
        'mpps_server_running': _mpps_server_running and mpps_port_open,
        'mwl_port': Config.DICOM_MWL_PORT,
        'storage_port': Config.DICOM_STORAGE_PORT,
        'mpps_port': mpps_port,
        'ae_title': Config.DICOM_AE_TITLE,
        'mwl_port_open': mwl_port_open,
        'storage_port_open': storage_port_open,
        'mpps_port_open': mpps_port_open,
        'threads': {
            'mwl_thread_alive': _mwl_server_thread.is_alive() if _mwl_server_thread else False,
            'storage_thread_alive': _storage_server_thread.is_alive() if _storage_server_thread else False,
            'mpps_thread_alive': _mpps_server_thread.is_alive() if _mpps_server_thread else False
        }
    }

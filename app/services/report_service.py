"""
Report Service
Business logic for report generation and management
"""
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.extensions import db
from app.models import Report, DicomImage, Patient, Admin
from app.utils.pdf_utils import generate_pdf_report
import secrets

logger = logging.getLogger(__name__)


def generate_report_number() -> str:
    """Generate unique report number"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_part = secrets.token_hex(4).upper()
    return f"RPT-{timestamp}-{random_part}"


def create_report(
    study_instance_uid: str,
    patient_id: Optional[str] = None,
    generated_by: Optional[int] = None,
    report_number: Optional[str] = None,
    notes: Optional[str] = None
) -> Report:
    """
    Create a new report record
    
    Args:
        study_instance_uid: Study Instance UID
        patient_id: Patient ID (optional)
        generated_by: Admin ID who generated the report (optional)
        report_number: Report number (optional, auto-generated if not provided)
        notes: Additional notes (optional)
    
    Returns:
        Report: Created report object
    """
    # Generate report number if not provided
    if not report_number:
        report_number = generate_report_number()
    
    # Get patient info
    patient = None
    patient_name = None
    if patient_id:
        patient = Patient.query.get(patient_id)
        if patient:
            patient_name = f"{patient.first_name} {patient.last_name}"
    
    # Get images for the study
    images = DicomImage.query.filter_by(study_instance_uid=study_instance_uid).all()
    
    # Create report record
    report = Report(
        report_number=report_number,
        study_instance_uid=study_instance_uid,
        patient_id=patient_id,
        patient_name=patient_name,
        report_date=datetime.now().date(),
        status='generating',
        image_count=len(images),
        generated_by=generated_by,
        notes=notes,
        file_path='',  # Will be set after PDF generation
        file_size=0
    )
    
    db.session.add(report)
    db.session.flush()  # Get the ID
    
    return report


def generate_report_pdf(report: Report) -> str:
    """
    Generate PDF file for a report
    
    Args:
        report: Report object
    
    Returns:
        str: Path to generated PDF file
    """
    # Get patient and images
    patient = Patient.query.get(report.patient_id) if report.patient_id else None
    images = DicomImage.query.filter_by(study_instance_uid=report.study_instance_uid).all()
    
    # Generate output path
    from app.config import Config
    reports_dir = Config.PDF_REPORTS_PATH
    os.makedirs(reports_dir, exist_ok=True, mode=0o755)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_uid = report.study_instance_uid.replace('.', '_')[:50]
    output_path = os.path.join(reports_dir, f"report_{report.report_number}_{safe_uid}_{timestamp}.pdf")
    output_path = os.path.abspath(output_path)
    
    # Generate PDF
    pdf_path = generate_pdf_report(
        study_instance_uid=report.study_instance_uid,
        patient=patient,
        images=images,
        output_path=output_path,
        report_number=report.report_number
    )
    
    # Update report with file info
    report.file_path = pdf_path
    if os.path.exists(pdf_path):
        report.file_size = os.path.getsize(pdf_path)
    report.status = 'completed'
    
    db.session.commit()
    
    logger.info(f"Report PDF generated: {pdf_path} (Report ID: {report.id})")
    return pdf_path


def get_report_by_id(report_id: int) -> Optional[Report]:
    """Get report by ID"""
    return Report.query.get(report_id)


def get_report_by_number(report_number: str) -> Optional[Report]:
    """Get report by report number"""
    return Report.query.filter_by(report_number=report_number).first()


def list_reports(
    patient_id: Optional[str] = None,
    study_instance_uid: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """
    List reports with pagination and filters
    
    Args:
        patient_id: Filter by patient ID
        study_instance_uid: Filter by study UID
        status: Filter by status
        page: Page number
        limit: Items per page
    
    Returns:
        dict: Reports and pagination info
    """
    query = Report.query
    
    # Apply filters
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if study_instance_uid:
        query = query.filter_by(study_instance_uid=study_instance_uid)
    if status:
        query = query.filter_by(status=status)
    
    # Order by date (newest first)
    query = query.order_by(Report.created_at.desc())
    
    # Pagination
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    return {
        'reports': [report.to_dict() for report in pagination.items],
        'pagination': {
            'page': pagination.page,
            'limit': limit,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }


def delete_report(report_id: int) -> bool:
    """
    Delete a report and its PDF file
    
    Args:
        report_id: Report ID
    
    Returns:
        bool: True if deleted, False if not found
    """
    report = Report.query.get(report_id)
    if not report:
        return False
    
    # Delete PDF file if exists
    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
            logger.info(f"Deleted report PDF file: {report.file_path}")
        except Exception as e:
            logger.error(f"Failed to delete report PDF file: {e}")
    
    # Delete database record
    db.session.delete(report)
    db.session.commit()
    
    logger.info(f"Deleted report: {report_id}")
    return True

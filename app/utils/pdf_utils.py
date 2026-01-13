"""
PDF Generation Utilities
"""
import os
from datetime import datetime
from app.config import Config


def generate_pdf_report(study_instance_uid, patient=None, images=None, output_path=None):
    """
    Generate PDF report for a DICOM study
    
    Args:
        study_instance_uid: Study Instance UID
        patient: Patient object (optional)
        images: List of DicomImage objects (optional)
        output_path: Output path for PDF (optional)
    
    Returns:
        str: Path to generated PDF file
    """
    # Create reports directory if it doesn't exist
    reports_dir = Config.PDF_REPORTS_PATH
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate output path
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(reports_dir, f"report_{study_instance_uid}_{timestamp}.pdf")
    
    # TODO: Implement actual PDF generation using WeasyPrint or ReportLab
    # For now, create a placeholder file
    with open(output_path, 'w') as f:
        f.write(f"PDF Report for Study: {study_instance_uid}\n")
        if patient:
            f.write(f"Patient: {patient.first_name} {patient.last_name}\n")
        if images:
            f.write(f"Images: {len(images)}\n")
    
    return output_path

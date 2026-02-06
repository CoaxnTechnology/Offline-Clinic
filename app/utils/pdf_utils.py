"""
PDF Generation Utilities using WeasyPrint
"""
import os
from datetime import datetime
from app.config import Config
from app.models import DicomImage, Patient
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not available. PDF generation will create placeholder files.")


def generate_pdf_report(study_instance_uid, patient=None, images=None, output_path=None, report_number=None):
    """
    Generate PDF report for a DICOM study using WeasyPrint
    
    Args:
        study_instance_uid: Study Instance UID
        patient: Patient object (optional)
        images: List of DicomImage objects (optional)
        output_path: Output path for PDF (optional)
        report_number: Report number (optional)
    
    Returns:
        str: Path to generated PDF file
    """
    # Create reports directory if it doesn't exist
    reports_dir = Config.PDF_REPORTS_PATH
    os.makedirs(reports_dir, exist_ok=True, mode=0o755)
    
    # Generate output path
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_uid = study_instance_uid.replace('.', '_')[:50]
        output_path = os.path.join(reports_dir, f"report_{safe_uid}_{timestamp}.pdf")
    
    # Ensure absolute path
    output_path = os.path.abspath(output_path)
    
    # Fetch data if not provided
    if not images:
        images = DicomImage.query.filter_by(study_instance_uid=study_instance_uid).all()
    
    if not patient and images:
        patient_id = images[0].patient_id if images else None
        if patient_id:
            patient = Patient.query.get(patient_id)
    
    # Get study info from first image
    study_info = {}
    if images:
        first_image = images[0]
        study_info = {
            'study_date': first_image.study_date,
            'study_time': first_image.study_time,
            'study_description': first_image.study_description,
            'accession_number': first_image.accession_number,
            'referring_physician': first_image.referring_physician,
            'institution_name': first_image.institution_name,
            'modality': first_image.modality,
        }
    
    # Generate HTML content
    html_content = generate_report_html(
        study_instance_uid=study_instance_uid,
        patient=patient,
        images=images,
        study_info=study_info,
        report_number=report_number
    )
    
    # Generate PDF
    if WEASYPRINT_AVAILABLE:
        try:
            # Generate PDF from HTML
            HTML(string=html_content).write_pdf(
                output_path,
                stylesheets=[CSS(string=get_report_css())]
            )
            logger.info(f"PDF report generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error generating PDF with WeasyPrint: {e}", exc_info=True)
            # Fallback to placeholder
            return generate_placeholder_report(output_path, study_instance_uid, patient, images)
    else:
        # Fallback to placeholder if WeasyPrint not available
        logger.warning("WeasyPrint not available, creating placeholder report")
        return generate_placeholder_report(output_path, study_instance_uid, patient, images)


def generate_report_html(study_instance_uid, patient=None, images=None, study_info=None, report_number=None):
    """Generate HTML content for PDF report"""
    
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
    patient_id = patient.id if patient else "N/A"
    patient_dob = patient.date_of_birth.strftime('%Y-%m-%d') if patient and patient.date_of_birth else "N/A"
    patient_gender = patient.gender if patient else "N/A"
    
    study_date = study_info.get('study_date').strftime('%Y-%m-%d') if study_info.get('study_date') else "N/A"
    study_desc = study_info.get('study_description', 'N/A')
    modality = study_info.get('modality', 'N/A')
    accession = study_info.get('accession_number', 'N/A')
    referring_physician = study_info.get('referring_physician', 'N/A')
    institution = study_info.get('institution_name', 'N/A')
    
    image_count = len(images) if images else 0
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>DICOM Study Report</title>
    </head>
    <body>
        <div class="header">
            <h1>DICOM Study Report</h1>
            <p class="report-number">Report Number: {report_number or 'N/A'}</p>
            <p class="report-date">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="section">
            <h2>Patient Information</h2>
            <table>
                <tr><td><strong>Patient ID:</strong></td><td>{patient_id}</td></tr>
                <tr><td><strong>Patient Name:</strong></td><td>{patient_name}</td></tr>
                <tr><td><strong>Date of Birth:</strong></td><td>{patient_dob}</td></tr>
                <tr><td><strong>Gender:</strong></td><td>{patient_gender}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Study Information</h2>
            <table>
                <tr><td><strong>Study Instance UID:</strong></td><td>{study_instance_uid}</td></tr>
                <tr><td><strong>Study Date:</strong></td><td>{study_date}</td></tr>
                <tr><td><strong>Study Description:</strong></td><td>{study_desc}</td></tr>
                <tr><td><strong>Modality:</strong></td><td>{modality}</td></tr>
                <tr><td><strong>Accession Number:</strong></td><td>{accession}</td></tr>
                <tr><td><strong>Referring Physician:</strong></td><td>{referring_physician}</td></tr>
                <tr><td><strong>Institution:</strong></td><td>{institution}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Images Summary</h2>
            <p><strong>Total Images:</strong> {image_count}</p>
    """
    
    # Add image thumbnails if available
    if images:
        html += "<div class='images-grid'>"
        for img in images[:10]:  # Limit to 10 thumbnails
            if img.thumbnail_path and os.path.exists(img.thumbnail_path):
                html += f"<div class='image-item'><p>Image {img.instance_number or 'N/A'}</p></div>"
        html += "</div>"
    
    html += """
        </div>
        
        <div class="footer">
            <p>This report was generated automatically from DICOM study data.</p>
            <p>Report generated by Clinic Backend System</p>
        </div>
    </body>
    </html>
    """
    
    return html


def get_report_css():
    """Get CSS styles for PDF report"""
    return """
    @page {
        size: A4;
        margin: 2cm;
    }
    
    body {
        font-family: Arial, sans-serif;
        font-size: 12pt;
        line-height: 1.6;
        color: #333;
    }
    
    .header {
        border-bottom: 3px solid #0066cc;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    
    .header h1 {
        color: #0066cc;
        margin: 0;
        font-size: 24pt;
    }
    
    .report-number, .report-date {
        margin: 5px 0;
        font-size: 10pt;
        color: #666;
    }
    
    .section {
        margin: 20px 0;
        page-break-inside: avoid;
    }
    
    .section h2 {
        color: #0066cc;
        border-bottom: 2px solid #0066cc;
        padding-bottom: 5px;
        font-size: 16pt;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
    }
    
    table td {
        padding: 8px;
        border-bottom: 1px solid #ddd;
    }
    
    table td:first-child {
        width: 200px;
        font-weight: bold;
        background-color: #f5f5f5;
    }
    
    .images-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        margin: 10px 0;
    }
    
    .image-item {
        border: 1px solid #ddd;
        padding: 10px;
        text-align: center;
    }
    
    .footer {
        margin-top: 30px;
        padding-top: 10px;
        border-top: 1px solid #ddd;
        font-size: 10pt;
        color: #666;
        text-align: center;
    }
    """


def generate_placeholder_report(output_path, study_instance_uid, patient=None, images=None):
    """Generate placeholder text file if WeasyPrint not available"""
    with open(output_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("DICOM STUDY REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Study Instance UID: {study_instance_uid}\n\n")
        
        if patient:
            f.write("Patient Information:\n")
            f.write(f"  ID: {patient.id}\n")
            f.write(f"  Name: {patient.first_name} {patient.last_name}\n")
            f.write(f"  DOB: {patient.date_of_birth}\n")
            f.write(f"  Gender: {patient.gender}\n\n")
        
        if images:
            f.write(f"Total Images: {len(images)}\n\n")
            f.write("Note: Full PDF generation requires WeasyPrint.\n")
            f.write("Install system dependencies:\n")
            f.write("  sudo apt install libpango-1.0-0 libharfbuzz0b libpangocairo-1.0-0 libcairo2\n")
    
    logger.warning(f"Placeholder report created: {output_path}")
    return output_path


def generate_prescription_pdf(prescription, patient=None, doctor=None, output_path=None):
    """
    Generate PDF prescription for a patient
    
    Args:
        prescription: Prescription object
        patient: Patient object (optional)
        doctor: Admin object (doctor who created prescription, optional)
        output_path: Output path for PDF (optional)
    
    Returns:
        str: Path to generated PDF file
    """
    # Create prescriptions directory if it doesn't exist
    prescriptions_dir = os.path.join(Config.PDF_REPORTS_PATH, "prescriptions")
    os.makedirs(prescriptions_dir, exist_ok=True, mode=0o755)
    
    # Generate output path
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_patient_id = prescription.patient_id.replace('/', '_')[:20]
        output_path = os.path.join(prescriptions_dir, f"prescription_{safe_patient_id}_{prescription.id}_{timestamp}.pdf")
    
    # Ensure absolute path
    output_path = os.path.abspath(output_path)
    
    # Fetch patient if not provided
    if not patient:
        from app.models import Patient
        patient = Patient.query.get(prescription.patient_id)
    
    # Generate HTML content
    html_content = generate_prescription_html(prescription, patient, doctor)
    
    # Generate PDF
    if WEASYPRINT_AVAILABLE:
        try:
            # Generate PDF from HTML
            HTML(string=html_content).write_pdf(
                output_path,
                stylesheets=[CSS(string=get_prescription_css())]
            )
            logger.info(f"Prescription PDF generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error generating prescription PDF with WeasyPrint: {e}", exc_info=True)
            # Fallback to placeholder
            return generate_placeholder_prescription(output_path, prescription, patient, doctor)
    else:
        # Fallback to placeholder if WeasyPrint not available
        logger.warning("WeasyPrint not available, creating placeholder prescription")
        return generate_placeholder_prescription(output_path, prescription, patient, doctor)


def generate_prescription_html(prescription, patient=None, doctor=None):
    """Generate HTML content for prescription PDF"""
    
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
    patient_id = patient.id if patient else prescription.patient_id
    patient_dob = patient.birth_date.strftime('%Y-%m-%d') if patient and patient.birth_date else "N/A"
    patient_gender = patient.gender if patient else "N/A"
    patient_age = ""
    if patient and patient.birth_date:
        today = datetime.now().date()
        age = today.year - patient.birth_date.year - ((today.month, today.day) < (patient.birth_date.month, patient.birth_date.day))
        patient_age = f"{age} years"
    
    doctor_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Dr. Unknown"

    # Build table rows for all medicines in this prescription
    rows_html = ""
    for item in prescription.items:
        med = item.get('medicine', '')
        dos = item.get('dosage', '')
        dur = item.get('duration_days', '')
        note = item.get('notes', '')
        rows_html += f"""
                    <tr>
                        <td>{med}</td>
                        <td>
                            <div class="dosage-detail">
                                <div class="dosage-line">{dos}</div>
                                {f'<div class="dosage-notes">{note}</div>' if note else ''}
                            </div>
                        </td>
                        <td>{dur} days</td>
                    </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Prescription</title>
    </head>
    <body>
        <div class="header">
            <h1>PRESCRIPTION</h1>
            <p class="prescription-date">Date: {datetime.now().strftime('%d-%m-%Y')}</p>
        </div>
        
        <div class="section">
            <h2>Patient Information</h2>
            <table>
                <tr><td><strong>Patient ID:</strong></td><td>{patient_id}</td></tr>
                <tr><td><strong>Patient Name:</strong></td><td>{patient_name}</td></tr>
                <tr><td><strong>Date of Birth:</strong></td><td>{patient_dob}</td></tr>
                <tr><td><strong>Age:</strong></td><td>{patient_age}</td></tr>
                <tr><td><strong>Gender:</strong></td><td>{patient_gender}</td></tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Prescription Details</h2>
            <table class="prescription-table">
                <thead>
                    <tr>
                        <th>Medicine</th>
                        <th>Dosage</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        
        <div class="section signature-section">
            <div class="signature">
                <p><strong>Prescribed by:</strong></p>
                <p class="doctor-name">{doctor_name}</p>
                <div class="signature-line"></div>
            </div>
        </div>
        
        <div class="footer">
            <p>This is a computer-generated prescription. Please follow the dosage instructions carefully.</p>
            <p>For any queries, please contact your healthcare provider.</p>
        </div>
    </body>
    </html>
    """
    
    return html


def get_prescription_css():
    """Get CSS styles for prescription PDF"""
    return """
    @page {
        size: A4;
        margin: 2cm;
    }
    
    body {
        font-family: Arial, sans-serif;
        font-size: 12pt;
        line-height: 1.6;
        color: #333;
    }
    
    .header {
        border-bottom: 3px solid #0066cc;
        padding-bottom: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .header h1 {
        color: #0066cc;
        margin: 0;
        font-size: 28pt;
        font-weight: bold;
    }
    
    .prescription-date {
        margin: 10px 0 0 0;
        font-size: 11pt;
        color: #666;
    }
    
    .section {
        margin: 25px 0;
        page-break-inside: avoid;
    }
    
    .section h2 {
        color: #0066cc;
        border-bottom: 2px solid #0066cc;
        padding-bottom: 5px;
        font-size: 16pt;
        margin-bottom: 15px;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
    }
    
    table td {
        padding: 10px;
        border-bottom: 1px solid #ddd;
        vertical-align: top;
    }
    
    table td:first-child {
        width: 180px;
        font-weight: bold;
        background-color: #f5f5f5;
    }
    
    .prescription-table {
        margin-top: 15px;
    }
    
    .prescription-table thead {
        background-color: #0066cc;
        color: white;
    }
    
    .prescription-table th {
        padding: 12px;
        text-align: left;
        font-weight: bold;
    }
    
    .prescription-table td {
        padding: 12px;
        border: 1px solid #ddd;
    }
    
    .dosage-detail {
        line-height: 1.8;
    }
    
    .dosage-detail span {
        display: block;
    }
    
    .notes {
        padding: 15px;
        background-color: #f9f9f9;
        border-left: 4px solid #0066cc;
        margin: 10px 0;
        font-style: italic;
    }
    
    .signature-section {
        margin-top: 50px;
        text-align: right;
    }
    
    .signature {
        display: inline-block;
        text-align: left;
        min-width: 250px;
    }
    
    .doctor-name {
        font-size: 14pt;
        font-weight: bold;
        margin: 10px 0;
        color: #0066cc;
    }
    
    .signature-line {
        border-top: 2px solid #333;
        margin-top: 40px;
        width: 200px;
    }
    
    .footer {
        margin-top: 50px;
        padding-top: 15px;
        border-top: 1px solid #ddd;
        font-size: 10pt;
        color: #666;
        text-align: center;
    }
    """


def generate_placeholder_prescription(output_path, prescription, patient=None, doctor=None):
    """Generate placeholder text file if WeasyPrint not available"""
    with open(output_path, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("PRESCRIPTION\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if patient:
            f.write("Patient Information:\n")
            f.write(f"  ID: {patient.id}\n")
            f.write(f"  Name: {patient.first_name} {patient.last_name}\n")
            f.write(f"  DOB: {patient.birth_date}\n")
            f.write(f"  Gender: {patient.gender}\n\n")
        
        f.write("Prescription Details:\n")
        for idx, item in enumerate(prescription.items, start=1):
            f.write(f"  Item {idx}:\n")
            f.write(f"    Medicine: {item.get('medicine', '')}\n")
            f.write(f"    Dosage: {item.get('dosage', '')}\n")
            f.write(f"    Duration: {item.get('duration_days', '')} days\n")
            note = item.get('notes') or ''
            if note:
                f.write(f"    Notes: {note}\n")
            f.write("\n")
        
        if doctor:
            f.write(f"Prescribed by: Dr. {doctor.first_name} {doctor.last_name}\n")
        
        f.write("\n")
        f.write("Note: Full PDF generation requires WeasyPrint.\n")
        f.write("Install system dependencies:\n")
        f.write("  sudo apt install libpango-1.0-0 libharfbuzz0b libpangocairo-1.0-0 libcairo2\n")
    
    logger.warning(f"Placeholder prescription created: {output_path}")
    return output_path

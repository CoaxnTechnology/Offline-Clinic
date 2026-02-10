"""
PDF Generation Utilities using WeasyPrint
"""
import os
from datetime import datetime
from app.config import Config
from app.models import DicomImage, Patient, Clinic, Prescription
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

# Styled prescription: WeasyPrint first; if missing/fails, ReportLab fallback (same style, no system deps).
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not available, using ReportLab for styled prescription PDFs.")
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


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
    # Create prescriptions directory under project root (so path works on any server)
    prescriptions_dir = os.path.join(Config.PROJECT_ROOT, Config.PDF_REPORTS_PATH, "prescriptions")
    os.makedirs(prescriptions_dir, exist_ok=True, mode=0o755)
    
    # Generate output path (absolute for writing)
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_patient_id = prescription.patient_id.replace('/', '_')[:20]
        filename = f"prescription_{safe_patient_id}_{prescription.id}_{timestamp}.pdf"
        output_path = os.path.join(prescriptions_dir, filename)
    else:
        output_path = os.path.abspath(output_path)
    
    # Return path relative to project root so DB works on any environment
    try:
        output_path_relative = os.path.relpath(output_path, Config.PROJECT_ROOT)
    except ValueError:
        output_path_relative = os.path.join(Config.PDF_REPORTS_PATH, "prescriptions", os.path.basename(output_path))
    
    # Fetch patient if not provided
    if not patient:
        from app.models import Patient
        patient = Patient.query.get(prescription.patient_id)
    
    # Generate HTML content
    html_content = generate_prescription_html(prescription, patient, doctor)
    
    # Generate PDF: WeasyPrint first, then ReportLab (styled), then minimal placeholder
    if WEASYPRINT_AVAILABLE:
        try:
            HTML(string=html_content).write_pdf(
                output_path,
                stylesheets=[CSS(string=get_prescription_css())]
            )
            logger.info(f"Prescription PDF generated (WeasyPrint): {output_path}")
            return output_path_relative
        except Exception as e:
            logger.error(f"WeasyPrint failed: {e}", exc_info=True)
    if REPORTLAB_AVAILABLE:
        try:
            _generate_prescription_pdf_reportlab(output_path, prescription, patient, doctor)
            logger.info(f"Prescription PDF generated (ReportLab): {output_path}")
            return output_path_relative
        except Exception as e:
            logger.error(f"ReportLab prescription PDF failed: {e}", exc_info=True)
    generate_placeholder_prescription(output_path, prescription, patient, doctor)
    return output_path_relative


def generate_patient_summary_pdf(patient, clinic=None, output_path=None, prescription=None):
    """
    Generate a PDF with patient details and clinic branding (name, logo, etc.).

    Returns a path relative to PROJECT_ROOT, e.g. 'reports/patients/patient_PAT001.pdf'.
    """
    # Determine clinic (for name/logo/header/footer)
    if clinic is None:
        try:
            clinic = Clinic.query.get(getattr(patient, "clinic_id", None))
        except Exception:
            clinic = None

    # Determine latest prescription (for summary table) if not provided
    if prescription is None:
        try:
            prescription = (
                Prescription.query.filter_by(patient_id=patient.id)
                .order_by(Prescription.created_at.desc())
                .first()
            )
        except Exception:
            prescription = None

    # Create directory under reports for patient + prescription summary PDFs
    # Use "prescriptions" in the path/name as requested.
    summaries_dir = os.path.join(
        Config.PROJECT_ROOT, Config.PDF_REPORTS_PATH, "prescriptions"
    )
    os.makedirs(summaries_dir, exist_ok=True, mode=0o755)

    # Default: one stable PDF per patient we overwrite
    if not output_path:
        filename = f"prescription_summary_{patient.id}.pdf"
        output_path = os.path.join(summaries_dir, filename)
    else:
        output_path = os.path.abspath(output_path)

    # Return path relative to project root (for links)
    try:
        output_path_relative = os.path.relpath(output_path, Config.PROJECT_ROOT)
    except ValueError:
        output_path_relative = os.path.join(
            Config.PDF_REPORTS_PATH, "patients", os.path.basename(output_path)
        )

    # Build HTML for patient summary (with optional latest prescription)
    html_content = _generate_patient_summary_html(patient, clinic, prescription)

    if WEASYPRINT_AVAILABLE:
        try:
            HTML(string=html_content).write_pdf(output_path)
            logger.info(f"Patient summary PDF generated (WeasyPrint): {output_path}")
            return output_path_relative
        except Exception as e:
            logger.error(
                f"Error generating patient summary PDF with WeasyPrint: {e}",
                exc_info=True,
            )

    if REPORTLAB_AVAILABLE:
        try:
            _generate_patient_summary_pdf_reportlab(output_path, patient, clinic, prescription)
            logger.info(f"Patient summary PDF generated (ReportLab): {output_path}")
            return output_path_relative
        except Exception as e:
            logger.error(
                f"Error generating patient summary PDF with ReportLab: {e}",
                exc_info=True,
            )

    # Fallback: minimal placeholder
    _generate_patient_summary_placeholder(output_path, patient, clinic)
    return output_path_relative


def _generate_patient_summary_html(patient, clinic=None, prescription=None):
    """HTML content for patient summary PDF with clinic branding."""
    logo_html = ""
    if clinic and clinic.logo_path:
        logo_path = (
            clinic.logo_path
            if os.path.isabs(clinic.logo_path)
            else os.path.join(Config.PROJECT_ROOT, clinic.logo_path)
        )
        if os.path.exists(logo_path):
            logo_html = f'<img src="{logo_path}" alt="Clinic Logo" style="height:80px;margin-bottom:10px;" />'

    clinic_name = clinic.name if clinic else "Clinic"
    clinic_addr = clinic.address or ""
    clinic_phone = clinic.phone or ""
    clinic_email = clinic.email or ""

    patient_name = f"{patient.first_name} {patient.last_name}".strip()
    patient_id = patient.id
    dob = patient.birth_date.strftime("%Y-%m-%d") if patient.birth_date else "N/A"
    gender = getattr(patient, "gender", None) or "N/A"
    phone = getattr(patient, "phone", None) or "N/A"
    email = getattr(patient, "email", None) or "N/A"
    height = getattr(patient, "height", None) or "N/A"
    weight = getattr(patient, "weight", None) or "N/A"
    blood_group = getattr(patient, "blood_group", None) or "N/A"
    medical_history = getattr(patient, "medical_history", None) or "N/A"
    allergies = getattr(patient, "allergies", None) or "N/A"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Patient Summary</title>
        <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}
        body {{
            font-family: Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.6;
            color: #333;
        }}
        .header {{
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .header h1 {{
            color: #0066cc;
            margin: 0;
            font-size: 24pt;
        }}
        .clinic-info {{
            font-size: 10pt;
            color: #555;
        }}
        .section {{
            margin: 20px 0;
            page-break-inside: avoid;
        }}
        .section h2 {{
            color: #0066cc;
            border-bottom: 2px solid #0066cc;
            padding-bottom: 5px;
            font-size: 16pt;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        table td {{
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        table td:first-child {{
            width: 200px;
            font-weight: bold;
            background-color: #f5f5f5;
        }}
        .section table.prescription-table {{
            margin-top: 10px;
        }}
        .prescription-table thead {{
            background-color: #0066cc;
            color: white;
        }}
        .prescription-table th {{
            padding: 8px;
            text-align: left;
        }}
        .prescription-table td {{
            padding: 8px;
            border: 1px solid #ddd;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
            font-size: 10pt;
            color: #666;
            text-align: center;
        }}
        </style>
    </head>
    <body>
        <div class="header">
            {logo_html}
            <h1>{clinic_name}</h1>
            <div class="clinic-info">
                <div>{clinic_addr}</div>
                <div>{clinic_phone}</div>
                <div>{clinic_email}</div>
            </div>
        </div>

        <div class="section">
            <h2>Patient Details</h2>
            <table>
                <tr><td>Patient ID</td><td>{patient_id}</td></tr>
                <tr><td>Patient Name</td><td>{patient_name}</td></tr>
                <tr><td>Date of Birth</td><td>{dob}</td></tr>
                <tr><td>Gender</td><td>{gender}</td></tr>
                <tr><td>Phone</td><td>{phone}</td></tr>
                <tr><td>Email</td><td>{email}</td></tr>
                <tr><td>Height</td><td>{height}</td></tr>
                <tr><td>Weight</td><td>{weight}</td></tr>
                <tr><td>Blood Group</td><td>{blood_group}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>Medical Information</h2>
            <table>
                <tr><td>Medical History</td><td>{medical_history}</td></tr>
                <tr><td>Allergies</td><td>{allergies}</td></tr>
            </table>
        </div>
    """

    # Append latest prescription section if available
    if prescription is not None:
        rows = []
        for item in prescription.items:
            med = item.get("medicine", "")
            dos = item.get("dosage", "")
            dur = item.get("duration_days", "")
            rows.append(
                f"<tr><td>{med}</td><td>{dos}</td><td>{dur} days</td></tr>"
            )
        rows_html = "".join(rows)
        html += f"""
        <div class="section">
            <h2>Latest Prescription</h2>
            <table>
                <tr><td>Prescription ID</td><td>{prescription.id}</td></tr>
                <tr><td>Date</td><td>{prescription.created_at.strftime('%Y-%m-%d %H:%M:%S') if prescription.created_at else 'N/A'}</td></tr>
            </table>
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
        """

    html += f"""
        <div class="footer">
            <p>Patient summary generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.</p>
        </div>
    </body>
    </html>
    """
    return html


def _generate_patient_summary_pdf_reportlab(output_path, patient, clinic=None, prescription=None):
    """Fallback patient summary PDF using ReportLab."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="PatientSummaryTitle",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=colors.HexColor("#0066cc"),
        alignment=1,
    )
    heading_style = ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#0066cc"),
    )
    normal = styles["Normal"]
    story = []

    clinic_name = clinic.name if clinic else "Clinic"
    story.append(Paragraph(clinic_name, title_style))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"Patient Summary generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            normal,
        )
    )
    story.append(Spacer(1, 20))

    # Patient details
    story.append(Paragraph("Patient Details", heading_style))
    pt_data = [
        ["Patient ID", patient.id],
        ["Patient Name", f"{patient.first_name} {patient.last_name}".strip()],
        [
            "Date of Birth",
            patient.birth_date.strftime("%Y-%m-%d") if patient.birth_date else "N/A",
        ],
        ["Gender", getattr(patient, "gender", None) or "N/A"],
        ["Phone", getattr(patient, "phone", None) or "N/A"],
        ["Email", getattr(patient, "email", None) or "N/A"],
        ["Height", getattr(patient, "height", None) or "N/A"],
        ["Weight", getattr(patient, "weight", None) or "N/A"],
        ["Blood Group", getattr(patient, "blood_group", None) or "N/A"],
    ]
    pt = Table(pt_data, colWidths=[5 * cm, 10 * cm])
    pt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(pt)
    story.append(Spacer(1, 20))

    # Medical info
    story.append(Paragraph("Medical Information", heading_style))
    med_data = [
        ["Medical History", getattr(patient, "medical_history", None) or "N/A"],
        ["Allergies", getattr(patient, "allergies", None) or "N/A"],
    ]
    mt = Table(med_data, colWidths=[5 * cm, 10 * cm])
    mt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f5f5")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(mt)
    story.append(Spacer(1, 20))

    # Latest prescription (optional)
    if prescription is not None:
        story.append(Paragraph("Latest Prescription", heading_style))
        presc_data = [["Medicine", "Dosage", "Duration"]]
        for item in prescription.items:
            med = item.get("medicine", "")
            dos = item.get("dosage", "")
            dur = f"{item.get('duration_days', '')} days"
            presc_data.append([med, dos, dur])
        pt3 = Table(presc_data, colWidths=[5 * cm, 7 * cm, 3 * cm])
        pt3.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0066cc")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(pt3)

    doc.build(story)


def _generate_patient_summary_placeholder(output_path, patient, clinic=None, prescription=None):
    """Minimal text-based PDF placeholder for patient summary."""
    lines = [
        "PATIENT SUMMARY",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Patient ID: {patient.id}",
        f"Name: {patient.first_name} {patient.last_name}",
        f"DOB: {patient.birth_date}",
        f"Gender: {getattr(patient, 'gender', None) or 'N/A'}",
        f"Phone: {getattr(patient, 'phone', None) or 'N/A'}",
        f"Email: {getattr(patient, 'email', None) or 'N/A'}",
        "",
        f"Medical History: {getattr(patient, 'medical_history', None) or 'N/A'}",
        f"Allergies: {getattr(patient, 'allergies', None) or 'N/A'}",
    ]

    if prescription is not None:
        lines.append("")
        lines.append("Latest Prescription:")
        for idx, item in enumerate(prescription.items, start=1):
            lines.append(f"  Item {idx}:")
            lines.append(f"    Medicine: {item.get('medicine', '')}")
            lines.append(f"    Dosage: {item.get('dosage', '')}")
            lines.append(f"    Duration: {item.get('duration_days', '')} days")

    y = 750
    content_parts = []
    for line in lines[:40]:
        if y < 40:
            break
        content_parts.append(f"BT /F1 11 Tf 50 {y} Td ({_pdf_escape(line)}) Tj ET")
        y -= 14
    content = "\n".join(content_parts)
    stream_body = content.encode("utf-8")
    stream_len = len(stream_body)

    parts = []
    parts.append(b"%PDF-1.4\n")
    parts.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    parts.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    parts.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
    )
    parts.append(f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode())
    parts.append(stream_body)
    parts.append(b"\nendstream\nendobj\n")

    body = b"".join(parts)
    xref_offset = len(body)
    offsets = [0]
    for i in range(1, 5):
        idx = body.find(f"{i} 0 obj".encode())
        offsets.append(idx if idx >= 0 else 0)
    xref = "xref\n0 5\n"
    xref += f"{offsets[0]:010d} 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n"
    trailer = (
        f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    )
    pdf = body + xref.encode() + trailer.encode()
    with open(output_path, "wb") as f:
        f.write(pdf)

    logger.warning(
        f"Placeholder patient summary (minimal PDF) created: {output_path}"
    )
    return output_path


def generate_prescription_html(prescription, patient=None, doctor=None):
    """Generate HTML content for prescription PDF (clinic-branded)."""
    
    # Resolve clinic for logo/name/address/phone
    clinic = None
    try:
        if doctor and getattr(doctor, "clinic_id", None):
            clinic = Clinic.query.get(doctor.clinic_id)
        elif patient and getattr(patient, "clinic_id", None):
            clinic = Clinic.query.get(patient.clinic_id)
    except Exception:
        clinic = None

    logo_html = ""
    if clinic and clinic.logo_path:
        logo_path = (
            clinic.logo_path
            if os.path.isabs(clinic.logo_path)
            else os.path.join(Config.PROJECT_ROOT, clinic.logo_path)
        )
        if os.path.exists(logo_path):
            logo_html = f'<img src="{logo_path}" alt="Clinic Logo" style="height:60px;margin-right:15px;" />'

    clinic_name = clinic.name if clinic else "Clinic"
    clinic_addr = clinic.address or ""
    clinic_phone = clinic.phone or ""
    clinic_email = clinic.email or ""

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
    department = getattr(doctor, "qualifications", None) or "General"

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
            <div class="clinic-block">
                <div class="logo">{logo_html}</div>
                <div class="clinic-text">
                    <h1>{clinic_name}</h1>
                    <p>{clinic_addr}</p>
                    <p>{clinic_phone}</p>
                    <p>{clinic_email}</p>
                </div>
            </div>
            <div class="prescription-meta">
                <p><strong>Prescription ID:</strong> {prescription.id}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y')}</p>
            </div>
        </div>
        
        <div class="section">
            <table class="patient-doctor-table">
                <tr>
                    <td>
                        <p><strong>Patient Name:</strong> {patient_name}</p>
                        <p><strong>Patient ID:</strong> {patient_id}</p>
                        <p><strong>Age / Gender:</strong> {patient_age or 'N/A'} / {patient_gender}</p>
                    </td>
                    <td>
                        <p><strong>Doctor:</strong> {doctor_name}</p>
                        <p><strong>Department:</strong> {department}</p>
                    </td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Prescription Details</h2>
            <table class="prescription-table">
                <thead>
                    <tr>
                        <th>Medicine</th>
                        <th>Dosage</th>
                        <th>Duration (Days)</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        
        <div class="section signature-section">
            <table class="signature-table">
                <tr>
                    <td class="sig-cell">
                        <div class="signature-line"></div>
                        <p>Patient Signature</p>
                    </td>
                    <td class="sig-cell">
                        <div class="signature-line"></div>
                        <p>Doctor Signature</p>
                    </td>
                </tr>
            </table>
        </div>

        <div class="footer">
            <p>This is a computer-generated prescription. Please follow the dosage instructions carefully.</p>
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
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }
    
    .clinic-block {
        display: flex;
        align-items: center;
    }
    
    .clinic-text h1 {
        color: #0066cc;
        margin: 0;
        font-size: 20pt;
        font-weight: bold;
    }
    
    .clinic-text p {
        margin: 2px 0;
        font-size: 10pt;
        color: #555;
    }
    
    .prescription-meta {
        text-align: right;
        font-size: 10pt;
        color: #333;
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
    
    .patient-doctor-table td {
        width: 50%;
        vertical-align: top;
        border: none;
        background-color: transparent;
    }
    
    .patient-doctor-table p {
        margin: 2px 0;
        font-size: 11pt;
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
    }
    
    .signature-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
    }
    
    .signature-table .sig-cell {
        width: 50%;
        text-align: center;
        border: none;
    }
    
    .signature-line {
        border-top: 2px solid #333;
        margin-top: 40px;
        width: 200px;
        margin-left: auto;
        margin-right: auto;
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


def _pdf_escape(s):
    s = str(s).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    return s[:80]


def _generate_prescription_pdf_reportlab(output_path, prescription, patient=None, doctor=None):
    """Styled prescription PDF using ReportLab (same look as WeasyPrint: blue header, tables, signature)."""
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='PrescriptionTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=6,
        alignment=1,
    )
    heading_style = ParagraphStyle(
        name='SectionHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#0066cc'),
        spaceAfter=8,
        borderPadding=(0, 0, 2, 0),
    )
    normal = styles['Normal']
    story = []

    # Header
    story.append(Paragraph("PRESCRIPTION", title_style))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", normal))
    story.append(Spacer(1, 16))

    # Patient info table
    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown"
    patient_id = patient.id if patient else prescription.patient_id
    patient_dob = patient.birth_date.strftime('%Y-%m-%d') if patient and patient.birth_date else "N/A"
    patient_gender = patient.gender if patient else "N/A"
    patient_age = ""
    if patient and patient.birth_date:
        today = datetime.now().date()
        age = today.year - patient.birth_date.year - ((today.month, today.day) < (patient.birth_date.month, patient.birth_date.day))
        patient_age = f"{age} years"
    story.append(Paragraph("Patient Information", heading_style))
    pt_data = [
        ["Patient ID:", patient_id],
        ["Patient Name:", patient_name],
        ["Date of Birth:", patient_dob],
        ["Age:", patient_age],
        ["Gender:", patient_gender],
    ]
    pt = Table(pt_data, colWidths=[5*cm, 10*cm])
    pt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(pt)
    story.append(Spacer(1, 20))

    # Prescription table
    story.append(Paragraph("Prescription Details", heading_style))
    presc_data = [["Medicine", "Dosage", "Duration"]]
    for item in prescription.items:
        med = item.get('medicine', '')
        dos = item.get('dosage', '')
        note = item.get('notes', '')
        if note:
            dos = f"{dos}\n{note}"
        presc_data.append([med, dos, f"{item.get('duration_days', '')} days"])
    pt2 = Table(presc_data, colWidths=[5*cm, 7*cm, 3*cm])
    pt2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(pt2)
    story.append(Spacer(1, 40))

    # Signature
    doctor_name = f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Dr. Unknown"
    story.append(Paragraph("<b>Prescribed by:</b>", normal))
    story.append(Paragraph(f'<font color="#0066cc" size="14"><b>{doctor_name}</b></font>', normal))
    story.append(Spacer(1, 30))
    story.append(Paragraph("_" * 30, normal))
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        "<i>This is a computer-generated prescription. Please follow the dosage instructions carefully.</i>",
        ParagraphStyle(name='Footer', parent=normal, fontSize=9, textColor=colors.grey, alignment=1)
    ))
    doc.build(story)


def generate_placeholder_prescription(output_path, prescription, patient=None, doctor=None):
    """Minimal valid PDF when WeasyPrint and ReportLab both unavailable."""
    lines = [
        "PRESCRIPTION",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    if patient:
        lines.extend([
            "Patient Information:",
            f"  ID: {patient.id}",
            f"  Name: {patient.first_name} {patient.last_name}",
            f"  DOB: {patient.birth_date}",
            f"  Gender: {patient.gender}",
            "",
        ])
    lines.append("Prescription Details:")
    for idx, item in enumerate(prescription.items, start=1):
        lines.append(f"  Item {idx}:")
        lines.append(f"    Medicine: {item.get('medicine', '')}")
        lines.append(f"    Dosage: {item.get('dosage', '')}")
        lines.append(f"    Duration: {item.get('duration_days', '')} days")
        note = item.get('notes') or ''
        if note:
            lines.append(f"    Notes: {note}")
        lines.append("")
    if doctor:
        lines.append(f"Prescribed by: Dr. {doctor.first_name} {doctor.last_name}")
    lines.append("(Generated without WeasyPrint - install for formatted PDFs)")

    y = 750
    content_parts = []
    for line in lines[:40]:
        if y < 40:
            break
        content_parts.append(f"BT /F1 11 Tf 50 {y} Td ({_pdf_escape(line)}) Tj ET")
        y -= 14
    content = "\n".join(content_parts)
    stream_body = content.encode('utf-8')
    stream_len = len(stream_body)

    parts = []
    parts.append(b"%PDF-1.4\n")
    # obj 1: Catalog
    parts.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # obj 2: Pages
    parts.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # obj 3: Page
    parts.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n")
    # obj 4: Content stream
    parts.append(f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode())
    parts.append(stream_body)
    parts.append(b"\nendstream\nendobj\n")

    body = b"".join(parts)
    xref_offset = len(body)
    offsets = [0]  # object 0 (free)
    for i in range(1, 5):
        idx = body.find(f"{i} 0 obj".encode())
        offsets.append(idx if idx >= 0 else 0)
    xref = "xref\n0 5\n"
    xref += f"{offsets[0]:010d} 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n"
    trailer = f"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    pdf = body + xref.encode() + trailer.encode()
    with open(output_path, 'wb') as f:
        f.write(pdf)

    logger.warning(f"Placeholder prescription (minimal PDF) created: {output_path}")
    return output_path

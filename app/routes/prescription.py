"""
Prescription API Routes
Handles prescription creation, deletion, and PDF download
"""

from flask import Blueprint, request, jsonify, send_file, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Patient, Prescription, Admin, Visit
from app.utils.decorators import require_role
from app.utils.audit import log_audit
from app.utils.pdf_utils import generate_prescription_pdf
import os
import logging
import json

logger = logging.getLogger(__name__)

prescription_bp = Blueprint("prescription", __name__, url_prefix="/api/prescriptions")


@prescription_bp.route("", methods=["POST"])
@jwt_required()
@require_role("doctor")
def create_prescription():
    """
    Create a new prescription and generate PDF

    Body:
        patient_id: Patient ID (required)
        visit_id: Visit ID (optional - links prescription to specific visit)
        medicine: Medicine name (required)
        dosage: Dosage format like "1-0-1" (required)
        duration_days: Duration in days (required)
        notes: Additional notes/instructions (optional)

    Returns:
        Prescription object with PDF path
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data:
            return jsonify({"success": False, "error": "Request body is required"}), 400

        patient_id = data.get("patient_id")
        visit_id = data.get("visit_id")  # Optional: link to specific visit
        medicine = data.get("medicine")
        dosage = data.get("dosage")
        duration_days = data.get("duration_days")
        notes = data.get("notes", "")
        items = data.get("items")  # Optional: list of medicines for one PDF

        # Validate required fields
        if not patient_id:
            return jsonify({"success": False, "error": "patient_id is required"}), 400

        # If items list is provided, use it; otherwise fall back to single medicine fields
        items_payload = None
        if items is not None:
            if not isinstance(items, list) or not items:
                return jsonify(
                    {"success": False, "error": "items must be a non-empty list"}
                ), 400

            normalized_items = []
            for idx, item in enumerate(items, start=1):
                med = (item.get("medicine") or "").strip()
                dos = (item.get("dosage") or "").strip()
                dur = item.get("duration_days")
                note = item.get("notes", "") or ""

                if not med:
                    return jsonify(
                        {"success": False, "error": f"Item {idx}: medicine is required"}
                    ), 400
                if not dos:
                    return jsonify(
                        {"success": False, "error": f"Item {idx}: dosage is required"}
                    ), 400
                try:
                    dur = int(dur)
                    if dur <= 0:
                        raise ValueError
                except (ValueError, TypeError):
                    return jsonify(
                        {
                            "success": False,
                            "error": f"Item {idx}: duration_days must be a positive integer",
                        }
                    ), 400

                normalized_items.append(
                    {
                        "medicine": med,
                        "dosage": dos,
                        "duration_days": dur,
                        "notes": note,
                    }
                )

            items_payload = normalized_items

            # For backward compatibility, copy first item into legacy fields
            first = normalized_items[0]
            medicine = first["medicine"]
            dosage = first["dosage"]
            duration_days = first["duration_days"]
            notes = first["notes"]

        # If no items list, use single-medicine fields
        if items_payload is None:
            if not medicine:
                return jsonify({"success": False, "error": "medicine is required"}), 400

            if not dosage:
                return jsonify({"success": False, "error": "dosage is required"}), 400

            if not duration_days:
                return jsonify(
                    {"success": False, "error": "duration_days is required"}
                ), 400

            # Validate duration_days is a positive integer
            try:
                duration_days = int(duration_days)
                if duration_days <= 0:
                    raise ValueError("Duration must be positive")
            except (ValueError, TypeError):
                return jsonify(
                    {
                        "success": False,
                        "error": "duration_days must be a positive integer",
                    }
                ), 400

        # Check if patient exists and is not deleted
        patient = (
            Patient.query.filter_by(id=patient_id)
            .filter(Patient.deleted_at.is_(None))
            .first()
        )
        if not patient:
            return jsonify(
                {"success": False, "error": f"Patient with ID {patient_id} not found"}
            ), 404

        # Get current user (doctor)
        user_id = int(get_jwt_identity())
        doctor = Admin.query.get(user_id)
        if not doctor:
            return jsonify({"success": False, "error": "Doctor not found"}), 404

        # Create prescription
        prescription = Prescription(
            patient_id=patient_id,
            visit_id=visit_id,
            medicine=medicine,
            dosage=dosage,
            duration_days=duration_days,
            notes=notes,
            created_by=user_id,
        )

        # If we received multiple items, store them in items_json
        if items_payload is not None:
            prescription.items_json = json.dumps(items_payload, ensure_ascii=False)

        db.session.add(prescription)
        db.session.flush()  # Get prescription.id

        # Generate PDF
        try:
            pdf_path = generate_prescription_pdf(
                prescription, patient=patient, doctor=doctor
            )
            prescription.pdf_path = pdf_path
            db.session.commit()

            # Audit log
            log_audit(
                "prescription",
                "create",
                user_id=user_id,
                entity_id=str(prescription.id),
                details={
                    "patient_id": patient_id,
                    "medicine_count": len(items_payload) if items_payload else 1,
                },
            )

            logger.info(
                f"Prescription {prescription.id} created for patient {patient_id} by doctor {user_id}"
            )

            return jsonify(
                {
                    "success": True,
                    "data": prescription.to_dict(),
                    "message": "Prescription created successfully",
                }
            ), 201

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating prescription PDF: {e}", exc_info=True)
            return jsonify(
                {"success": False, "error": f"Failed to generate PDF: {str(e)}"}
            ), 500

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating prescription: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"An error occurred: {str(e)}"}), 500


@prescription_bp.route("/<int:prescription_id>", methods=["DELETE"])
@jwt_required()
@require_role("doctor")
def delete_prescription(prescription_id):
    """
    Delete a prescription and its PDF.
    Only doctors can delete.
    """
    try:
        prescription = Prescription.query.get(prescription_id)

        if not prescription:
            return jsonify(
                {
                    "success": False,
                    "error": f"Prescription with ID {prescription_id} not found",
                }
            ), 404

        # Remove PDF file from disk (resolve relative path if needed)
        if prescription.pdf_path:
            from app.config import Config

            full_path = (
                prescription.pdf_path
                if os.path.isabs(prescription.pdf_path)
                else os.path.join(Config.PROJECT_ROOT, prescription.pdf_path)
            )
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except OSError:
                    pass

        # Audit log before deletion
        user_id = int(get_jwt_identity())
        log_audit(
            "prescription",
            "delete",
            user_id=user_id,
            entity_id=str(prescription_id),
            details={"patient_id": prescription.patient_id},
        )

        db.session.delete(prescription)
        db.session.commit()

        return jsonify(
            {"success": True, "message": "Prescription deleted successfully"}
        ), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting prescription: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"An error occurred: {str(e)}"}), 500


@prescription_bp.route("/<int:prescription_id>", methods=["GET"])
@jwt_required()
def get_prescription(prescription_id):
    """
    Get a single prescription by ID.
    Returns all medicines (items) for that prescription.
    """
    try:
        prescription = Prescription.query.get(prescription_id)

        if not prescription:
            return jsonify(
                {
                    "success": False,
                    "error": f"Prescription with ID {prescription_id} not found",
                }
            ), 404

        return jsonify({"success": True, "data": prescription.to_dict()}), 200

    except Exception as e:
        logger.error(f"Error getting prescription: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"An error occurred: {str(e)}"}), 500


@prescription_bp.route("/<int:prescription_id>/download", methods=["GET"])
@jwt_required()
def download_prescription_pdf(prescription_id):
    """
    Download or preview prescription PDF.
    Query param: inline=1 or preview=1 to open in browser/Postman (Content-Disposition: inline).
    """
    try:
        prescription = Prescription.query.get(prescription_id)
        if not prescription:
            return jsonify(
                {
                    "success": False,
                    "error": f"Prescription with ID {prescription_id} not found",
                }
            ), 404

        from app.config import Config

        pdf_path = prescription.pdf_path
        if not pdf_path:
            return jsonify(
                {
                    "success": False,
                    "error": "PDF path not set. Regenerate the prescription.",
                }
            ), 404

        # Resolve full path: absolute as-is, else relative to PROJECT_ROOT then CWD
        if os.path.isabs(pdf_path):
            full_path = pdf_path
        else:
            full_path = os.path.join(Config.PROJECT_ROOT, pdf_path)
        if not os.path.exists(full_path):
            full_path = os.path.abspath(os.path.join(os.getcwd(), pdf_path))
        if not os.path.exists(full_path):
            return jsonify(
                {
                    "success": False,
                    "error": "PDF file not found on server. Create the prescription on this server or copy reports/ folder.",
                    "resolved_path": full_path,
                }
            ), 404

        # inline=1 or preview=1 → show in browser; otherwise force download
        inline = request.args.get("inline", request.args.get("preview")) in (
            "1",
            "true",
            "yes",
        )
        download_name = f"prescription_{prescription.patient_id}_{prescription.id}.pdf"
        file_size = os.path.getsize(full_path)
        with open(full_path, "rb") as f:
            body = f.read()
        from flask import Response

        resp = Response(body, status=200, mimetype="application/pdf")
        resp.headers["Content-Type"] = "application/pdf"
        resp.headers["Content-Length"] = str(file_size)
        resp.headers["Content-Disposition"] = (
            f'{"inline" if inline else "attachment"}; filename="{download_name}"'
        )
        resp.headers["Cache-Control"] = "no-store"
        return resp

    except Exception as e:
        logger.error(f"Error downloading prescription PDF: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"An error occurred: {str(e)}"}), 500


@prescription_bp.route("/patient/<patient_id>", methods=["GET"])
@jwt_required()
def get_patient_prescriptions(patient_id):
    """
    Get all prescriptions for a specific patient

    Query params:
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)

    Returns:
        List of prescriptions for the patient
    """
    try:
        # Check if patient exists
        patient = (
            Patient.query.filter_by(id=patient_id)
            .filter(Patient.deleted_at.is_(None))
            .first()
        )
        if not patient:
            return jsonify(
                {"success": False, "error": f"Patient with ID {patient_id} not found"}
            ), 404

        # Validate pagination
        try:
            page = request.args.get("page", 1, type=int)
            limit = request.args.get("limit", 20, type=int)
        except (ValueError, TypeError):
            return jsonify(
                {"success": False, "error": "Invalid pagination parameters"}
            ), 400

        if page < 1:
            page = 1
        if limit < 1:
            limit = 20
        if limit > 100:
            limit = 100

        # Query prescriptions for patient
        query = Prescription.query.filter_by(patient_id=patient_id)
        query = query.order_by(Prescription.created_at.desc())

        # Paginate
        pagination = query.paginate(page=page, per_page=limit, error_out=False)

        return jsonify(
            {
                "success": True,
                "data": [prescription.to_dict() for prescription in pagination.items],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": pagination.total,
                    "pages": pagination.pages,
                },
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting patient prescriptions: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"An error occurred: {str(e)}"}), 500


@prescription_bp.route("/appointment/<int:appointment_id>", methods=["GET"])
@jwt_required()
def get_appointment_prescription(appointment_id):
    """
    Get prescription for a specific appointment.

    Each appointment has at most one Visit, and each Visit has at most one Prescription,
    so this returns a single prescription (or 404 if none).
    """
    try:
        # Find the Visit for this appointment
        visit = Visit.query.filter_by(appointment_id=appointment_id, deleted_at=None).first()
        if not visit:
            return jsonify(
                {
                    "success": False,
                    "error": f"Visit for appointment {appointment_id} not found",
                }
            ), 404

        # Visit → Prescription (one-to-one via backref)
        prescription = visit.prescription
        if not prescription:
            return jsonify(
                {
                    "success": False,
                    "error": f"No prescription found for appointment {appointment_id}",
                }
            ), 404

        return jsonify({"success": True, "data": prescription.to_dict()}), 200

    except Exception as e:
        logger.error(
            f"Error getting prescription for appointment {appointment_id}: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"An error occurred: {str(e)}",
                }
            ),
            500,
        )

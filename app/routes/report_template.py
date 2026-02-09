"""
Report Template API Routes
Manages structured OB/GYN report templates
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import ReportTemplate, Admin
from app.utils.decorators import require_role
from app.utils.audit import log_audit
import logging
import json

logger = logging.getLogger(__name__)

template_bp = Blueprint('report_template', __name__, url_prefix='/api/report-templates')


@template_bp.route('', methods=['GET'])
@jwt_required()
def list_templates():
    """
    List report templates with filters
    
    Query params:
        template_type: Filter by type ('OB' or 'GYN')
        category: Filter by category
        language: Filter by language ('en' or 'fr')
        is_active: Filter by active status (true/false)
    """
    try:
        template_type = request.args.get('template_type')
        category = request.args.get('category')
        language = request.args.get('language')
        is_active = request.args.get('is_active')
        
        query = ReportTemplate.query
        
        if template_type:
            query = query.filter_by(template_type=template_type)
        if category:
            query = query.filter_by(category=category)
        if language:
            query = query.filter_by(language=language)
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            query = query.filter_by(is_active=is_active_bool)
        
        query = query.order_by(ReportTemplate.display_order, ReportTemplate.name)
        templates = query.all()
        
        return jsonify({
            'success': True,
            'data': {
                'templates': [template.to_dict() for template in templates],
                'total': len(templates)
            }
        })
    
    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        error_msg = 'Failed to list templates' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@template_bp.route('/<int:template_id>', methods=['GET'])
@jwt_required()
def get_template(template_id):
    """Get template details by ID"""
    try:
        template = ReportTemplate.query.get(template_id)
        if not template:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': template.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}", exc_info=True)
        error_msg = 'Failed to get template' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@template_bp.route('', methods=['POST'])
@jwt_required()
@require_role('doctor', 'admin')
def create_template():
    """
    Create a new report template
    Access: doctor, admin
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        
        # Validate required fields
        required_fields = ['name', 'code', 'template_type', 'category', 'fields']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        # Check if code already exists
        if ReportTemplate.query.filter_by(code=data['code']).first():
            return jsonify({
                'success': False,
                'error': f'Template with code "{data["code"]}" already exists'
            }), 400
        
        # Validate fields structure
        if not isinstance(data['fields'], list):
            return jsonify({
                'success': False,
                'error': 'fields must be a list of field definitions'
            }), 400
        
        # Create template
        template = ReportTemplate(
            name=data['name'],
            code=data['code'],
            template_type=data['template_type'],
            category=data['category'],
            language=data.get('language', 'en'),
            is_active=data.get('is_active', True),
            display_order=data.get('display_order', 0)
        )
        
        template.set_fields(data['fields'])
        if 'required_fields' in data:
            template.set_required_fields(data['required_fields'])
        
        db.session.add(template)
        db.session.commit()
        
        log_audit('report_template', 'create', user_id=user_id, entity_id=str(template.id), details={'code': template.code})
        
        return jsonify({
            'success': True,
            'message': 'Template created successfully',
            'data': template.to_dict()
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating template: {e}", exc_info=True)
        db.session.rollback()
        error_msg = 'Failed to create template' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@template_bp.route('/<int:template_id>', methods=['PUT'])
@jwt_required()
@require_role('doctor', 'admin')
def update_template(template_id):
    """
    Update a report template
    Access: doctor, admin
    """
    try:
        user_id = int(get_jwt_identity())
        template = ReportTemplate.query.get(template_id)
        if not template:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404
        
        data = request.get_json() or {}
        
        # Update allowed fields
        if 'name' in data:
            template.name = data['name']
        if 'template_type' in data:
            template.template_type = data['template_type']
        if 'category' in data:
            template.category = data['category']
        if 'language' in data:
            template.language = data['language']
        if 'is_active' in data:
            template.is_active = data['is_active']
        if 'display_order' in data:
            template.display_order = data['display_order']
        if 'fields' in data:
            if not isinstance(data['fields'], list):
                return jsonify({
                    'success': False,
                    'error': 'fields must be a list'
                }), 400
            template.set_fields(data['fields'])
        if 'required_fields' in data:
            template.set_required_fields(data['required_fields'])
        
        db.session.commit()
        log_audit('report_template', 'update', user_id=user_id, entity_id=str(template_id), details={'code': template.code})
        
        return jsonify({
            'success': True,
            'message': 'Template updated successfully',
            'data': template.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}", exc_info=True)
        db.session.rollback()
        error_msg = 'Failed to update template' if not current_app.debug else str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

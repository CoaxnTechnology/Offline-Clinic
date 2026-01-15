"""
Health check endpoints for monitoring and load balancers
"""
from flask import Blueprint, jsonify
from app.extensions import db
from datetime import datetime

health_bp = Blueprint('health', __name__, url_prefix='/health')


@health_bp.route('', methods=['GET'])
@health_bp.route('/ping', methods=['GET'])
def health_check():
    """Basic health check - no database connection"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'clinic-backend'
    }), 200


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check - includes database connection"""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    return jsonify({
        'status': 'ready' if db_status == 'connected' else 'not_ready',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    }), 200 if db_status == 'connected' else 503


@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """Liveness check for Kubernetes/containers"""
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@health_bp.route('/dicom', methods=['GET'])
def dicom_health_check():
    """DICOM servers health check"""
    try:
        from app.services.dicom_service import get_server_status
        status = get_server_status()
        
        return jsonify({
            'status': 'healthy' if (status.get('mwl_server_running') and status.get('storage_server_running')) else 'degraded',
            'dicom': status,
            'timestamp': datetime.utcnow().isoformat()
        }), 200 if (status.get('mwl_server_running') and status.get('storage_server_running')) else 503
    
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

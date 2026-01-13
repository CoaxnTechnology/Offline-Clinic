from flask import Flask, jsonify, request
from .extensions import db, migrate, bcrypt, login_manager, celery
import logging
import os

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name=None):
    """Create Flask application factory"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name:
        from app.config import config
        app.config.from_object(config.get(config_name, config['default']))
    else:
        from app.config import get_config
        app.config.from_object(get_config())
    
    # Ensure production mode if FLASK_ENV is production
    if os.getenv('FLASK_ENV') == 'production':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
    
    # Initialize extensions first (before error handlers)
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    # Initialize Celery
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        task_serializer=app.config['CELERY_TASK_SERIALIZER'],
        accept_content=app.config['CELERY_ACCEPT_CONTENT'],
        result_serializer=app.config['CELERY_RESULT_SERIALIZER'],
        timezone=app.config['CELERY_TIMEZONE'],
        enable_utc=app.config['CELERY_ENABLE_UTC'],
    )
    
    # Make celery tasks work with Flask app context
    class FlaskAppContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = FlaskAppContextTask
    
    # Global error handler
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {error}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error. Check server logs for details.'
        }), 500
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found'
        }), 404
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500

    # Setup logging
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
    
    # Production: Set max content length for file uploads
    app.config['MAX_CONTENT_LENGTH'] = app.config.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024)  # 100MB
    
    # Security headers middleware
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        if not app.debug:
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            # Only add HSTS if using HTTPS
            if request.is_secure:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # Production: Request timeout handler
    @app.before_request
    def before_request():
        """Set request timeout and validate"""
        # Production: Log slow requests (can be enhanced with middleware)
        pass
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.session_protection = 'strong'
    
    # User loader function - Flask-Login calls this to get user
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Admin
        return Admin.query.get(int(user_id))
    
    # Unauthorized handler - returns JSON instead of redirect
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import jsonify
        return jsonify({
            'success': False,
            'error': 'Authentication required'
        }), 401

    # Import models to register them with SQLAlchemy
    with app.app_context():
        from .models import Patient, Appointment, Admin, DicomImage, DicomMeasurement  # This is essential
        
        # Register blueprints
        from .routes import auth_bp, patient_bp, appointment_bp, admin_bp, dicom_bp, health_bp
        app.register_blueprint(health_bp)  # Register health check first
        app.register_blueprint(auth_bp)
        app.register_blueprint(patient_bp)
        app.register_blueprint(appointment_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(dicom_bp)
        
        # Auto-start DICOM servers if enabled (default: True)
        auto_start_dicom = os.getenv('AUTO_START_DICOM', 'true').lower() == 'true'
        if auto_start_dicom:
            try:
                from app.services.dicom_service import start_dicom_servers, get_server_status
                logger.info("Auto-starting DICOM servers...")
                start_dicom_servers()
                
                # Wait a moment and verify
                import time
                time.sleep(1)
                status = get_server_status()
                if status.get('mwl_server_running') and status.get('storage_server_running'):
                    logger.info("✅ DICOM servers started successfully")
                    logger.info(f"   MWL Server: Port {status.get('mwl_port')}")
                    logger.info(f"   Storage Server: Port {status.get('storage_port')}")
                    logger.info(f"   AE Title: {status.get('ae_title')}")
                else:
                    logger.warning("⚠️  DICOM servers may not have started properly. Check logs.")
            except Exception as e:
                logger.error(f"Failed to auto-start DICOM servers: {e}", exc_info=True)
                logger.warning("You can start DICOM servers manually via: POST /api/dicom/server/start")

    return app
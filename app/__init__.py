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
    
    # Initialize JWT
    from flask_jwt_extended import JWTManager
    jwt = JWTManager(app)
    
    # Initialize CORS
    from app.utils.cors import init_cors
    init_cors(app)
    
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
        from .models import Patient, Appointment, Admin, DicomImage, DicomMeasurement, Prescription, Visit, ReportTemplate, Report, AuditLog, Clinic  # This is essential
        
        # Register blueprints
        from .routes import auth_bp, patient_bp, appointment_bp, admin_bp, dicom_bp, health_bp, reporting_bp, prescription_bp, visit_bp, template_bp
        from .routes.super_admin import super_admin_bp
        app.register_blueprint(health_bp)  # Register health check first
        app.register_blueprint(auth_bp)
        app.register_blueprint(patient_bp)
        app.register_blueprint(appointment_bp)
        app.register_blueprint(admin_bp)  # /api/doctors
        app.register_blueprint(admin_bp, url_prefix='/api/receptionists', name='receptionist')  # Alias
        app.register_blueprint(dicom_bp)
        app.register_blueprint(reporting_bp)
        app.register_blueprint(prescription_bp)
        app.register_blueprint(visit_bp)
        app.register_blueprint(template_bp)
        app.register_blueprint(super_admin_bp)
        
        # Auto-start DICOM servers if enabled (default: True). Skip in CI to avoid port conflicts.
        in_ci = os.getenv('CI', '').lower() == 'true' or os.getenv('GITHUB_ACTIONS', '').lower() == 'true'
        auto_start_dicom = not in_ci and os.getenv('AUTO_START_DICOM', 'true').lower() == 'true'
        if auto_start_dicom:
            import time
            from app.services.dicom_service import start_dicom_servers, get_server_status
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info("Auto-starting DICOM servers%s...", f" (attempt {attempt}/{max_attempts})" if attempt > 1 else "")
                    start_dicom_servers()
                    time.sleep(1)
                    status = get_server_status()
                    if status.get('mwl_server_running') and status.get('storage_server_running'):
                        logger.info("✅ DICOM servers started successfully")
                        logger.info(f"   MWL Server: Port {status.get('mwl_port')}")
                        logger.info(f"   Storage Server: Port {status.get('storage_port')}")
                        logger.info(f"   AE Title: {status.get('ae_title')}")
                        break
                    else:
                        logger.warning("⚠️  DICOM servers may not have started properly. Check logs.")
                        break
                except Exception as e:
                    port_in_use = "port" in str(e).lower() or "already in use" in str(e).lower()
                    if port_in_use and attempt < max_attempts:
                        logger.warning("DICOM ports in use (e.g. after restart), retrying in 2s: %s", e)
                        time.sleep(2)
                    else:
                        logger.error("Failed to auto-start DICOM servers: %s", e, exc_info=True)
                        logger.warning("You can start DICOM servers manually via: POST /api/dicom/server/start")
                        break
        elif in_ci:
            logger.info("Skipping DICOM auto-start (CI environment). Set AUTO_START_DICOM=true to override.")

    return app

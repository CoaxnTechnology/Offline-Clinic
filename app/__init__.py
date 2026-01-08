from flask import Flask
from .extensions import db, migrate, bcrypt, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
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
        from .models import Patient, Appointment, Admin  # This is essential
        
        # Register blueprints
        from .routes import auth_bp, patient_bp, appointment_bp
        app.register_blueprint(auth_bp)
        app.register_blueprint(patient_bp)
        app.register_blueprint(appointment_bp)

    return app
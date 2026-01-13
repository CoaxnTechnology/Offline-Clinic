"""
Middleware for production security and performance
"""
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)


def setup_middleware(app):
    """Setup production middleware"""
    
    @app.before_request
    def before_request():
        """Log requests in production"""
        if not app.debug:
            logger.info(f"{request.method} {request.path} - {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        """Add security headers and CORS if needed"""
        # Security headers (already in __init__.py, but can add more here)
        if not app.debug:
            # Prevent clickjacking
            response.headers['X-Frame-Options'] = 'DENY'
            # Prevent MIME type sniffing
            response.headers['X-Content-Type-Options'] = 'nosniff'
            # XSS protection
            response.headers['X-XSS-Protection'] = '1; mode=block'
            # Referrer policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    
    @app.before_first_request
    def create_tables():
        """Ensure database tables exist"""
        from app.extensions import db
        try:
            db.create_all()
        except Exception as e:
            logger.error(f"Error creating tables: {e}")

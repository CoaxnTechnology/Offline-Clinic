"""
WSGI entry point for production deployment
Used by Gunicorn, uWSGI, and other WSGI servers
"""
from app import create_app

# Create Flask app instance
application = app = create_app()

if __name__ == '__main__':
    # For development only
    application.run(debug=True)

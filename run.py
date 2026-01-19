"""
Development server entry point
Run the Flask application with: python run.py
"""
from app import create_app
import os

# Create Flask app instance
app = create_app()

if __name__ == '__main__':
    # Get host and port from environment or use defaults
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"""
    ========================================
    Starting Clinic Backend Server
    ========================================
    Host: {host}
    Port: {port}
    Debug: {debug}
    Environment: {os.getenv('FLASK_ENV', 'development')}
    ========================================
    
    DICOM servers will start automatically!
    MWL Port: {os.getenv('DICOM_MWL_PORT', '11112')}
    Storage Port: {os.getenv('DICOM_STORAGE_PORT', '11113')}
    ========================================
    """)
    
    # Run the Flask app
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True  # Allow multiple requests
    )

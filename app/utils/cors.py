"""
CORS Configuration
Centralized CORS settings for the application
"""

# CORS Configuration - Allow all origins
CORS_CONFIG = {
    "origins": "*",  # Allow any origin/port
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    "allow_headers": [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
    ],
    "expose_headers": [
        "Content-Type",
        "Authorization",
    ],
    "supports_credentials": True,
    "max_age": 86400,  # 24 hours
}


def init_cors(app):
    """
    Initialize CORS for the Flask application
    """
    from flask_cors import CORS
    
    CORS(app, 
         resources={r"/*": {"origins": CORS_CONFIG["origins"]}},
         methods=CORS_CONFIG["methods"],
         allow_headers=CORS_CONFIG["allow_headers"],
         expose_headers=CORS_CONFIG["expose_headers"],
         supports_credentials=CORS_CONFIG["supports_credentials"],
         max_age=CORS_CONFIG["max_age"])
    
    app.logger.info("CORS enabled for all origins")

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20
    }

    # DICOM Storage Paths
    DICOM_STORAGE_PATH = os.getenv('DICOM_STORAGE_PATH', 'dicom_files')
    THUMBNAIL_STORAGE_PATH = os.getenv('THUMBNAIL_STORAGE_PATH', 'thumbnails')
    PDF_REPORTS_PATH = os.getenv('PDF_REPORTS_PATH', 'reports')
    
    # DICOM Server Configuration
    DICOM_MWL_PORT = int(os.getenv('DICOM_MWL_PORT', '11112'))
    DICOM_STORAGE_PORT = int(os.getenv('DICOM_STORAGE_PORT', '11113'))
    DICOM_AE_TITLE = os.getenv('DICOM_AE_TITLE', 'STORESCP')
    
    # DICOM Production Settings
    DICOM_MAX_FILE_SIZE = int(os.getenv('DICOM_MAX_FILE_SIZE', '104857600'))  # 100MB default
    DICOM_CONNECTION_TIMEOUT = int(os.getenv('DICOM_CONNECTION_TIMEOUT', '30'))  # seconds
    DICOM_MAX_CONCURRENT_STORES = int(os.getenv('DICOM_MAX_CONCURRENT_STORES', '10'))
    DICOM_ENABLE_COMPRESSION = os.getenv('DICOM_ENABLE_COMPRESSION', 'true').lower() == 'true'
    DICOM_STORAGE_QUOTA_GB = int(os.getenv('DICOM_STORAGE_QUOTA_GB', '100'))  # 100GB default
    
    # Celery Configuration
    CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')
    
    # Email Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@clinic.com')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Security
    SESSION_COOKIE_SECURE = False  # Set to True when using HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Ensure SECRET_KEY is set
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY or SECRET_KEY == 'dev-secret-key-change-in-production':
        raise ValueError("SECRET_KEY environment variable must be set in production and must not be the default value")
    
    # Database connection pool for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_size': 20,
        'max_overflow': 40,
        'connect_args': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'
        }
    }
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING')
    
    # Production: File upload limits
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '104857600'))  # 100MB
    
    # Production: Rate limiting (if using Flask-Limiter)
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'false').lower() == 'true'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on FLASK_ENV"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])

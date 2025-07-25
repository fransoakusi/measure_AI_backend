"""
Configuration settings for Body Measurement AI Flask application
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    EXPORT_FOLDER = os.path.join(os.getcwd(), 'exports')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Database Settings
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/body_measurements'
    MONGO_DBNAME = os.environ.get('MONGO_DBNAME') or 'body_measurements'
    
    # Computer Vision Settings
    CV_CONFIDENCE_THRESHOLD = float(os.environ.get('CV_CONFIDENCE_THRESHOLD', '0.5'))
    CV_MIN_DETECTION_CONFIDENCE = float(os.environ.get('CV_MIN_DETECTION_CONFIDENCE', '0.5'))
    CV_MIN_TRACKING_CONFIDENCE = float(os.environ.get('CV_MIN_TRACKING_CONFIDENCE', '0.5'))
    
    # Measurement Settings
    DEFAULT_UNITS = os.environ.get('DEFAULT_UNITS', 'inches')  # inches or cm
    REFERENCE_HEIGHT_PIXELS = int(os.environ.get('REFERENCE_HEIGHT_PIXELS', '500'))
    AVERAGE_HUMAN_HEIGHT_INCHES = float(os.environ.get('AVERAGE_HUMAN_HEIGHT_INCHES', '68'))
    
    # PDF Generation Settings
    PDF_COMPANY_NAME = os.environ.get('PDF_COMPANY_NAME', 'TailorMeasure AI')
    PDF_COMPANY_ADDRESS = os.environ.get('PDF_COMPANY_ADDRESS', 'Professional Tailoring Solutions')
    PDF_LOGO_PATH = os.environ.get('PDF_LOGO_PATH', None)
    
    # API Settings
    API_TITLE = 'Body Measurement AI API'
    API_VERSION = 'v1'
    API_DESCRIPTION = 'AI-powered body measurement extraction from photos'
    
    # Rate Limiting (if needed)
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # Security
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
    
    # Performance
    CLEANUP_INTERVAL_HOURS = int(os.environ.get('CLEANUP_INTERVAL_HOURS', '24'))
    MAX_TEMP_FILE_AGE_HOURS = int(os.environ.get('MAX_TEMP_FILE_AGE_HOURS', '1'))
    
    @staticmethod
    def allowed_file(filename):
        """Check if uploaded file has allowed extension"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = 'WARNING'
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    MONGO_URI = 'mongodb://localhost:27017/body_measurements_test'
    MONGO_DBNAME = 'body_measurements_test'
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'test_uploads')
    EXPORT_FOLDER = os.path.join(os.getcwd(), 'test_exports')

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
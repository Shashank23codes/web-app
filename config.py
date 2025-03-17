from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'root')
    MYSQL_DB = 'food_donation_system'
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size 
    STATIC_FOLDER = 'static'
    CSS_FOLDER = 'static/css'
    JS_FOLDER = 'static/js'
    UPLOADS_FOLDER = 'static/uploads'
    DATETIME_FORMAT = '%Y-%m-%d %H:%M' 

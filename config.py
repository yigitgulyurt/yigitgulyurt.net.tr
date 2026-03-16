import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-change-in-prod'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///yigitgulyurt.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
    CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL') or 'yigit@yigitgulyurt.net.tr'
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'app', 'static', 'img')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    SERVER_NAME = os.environ.get('SERVER_NAME') or 'yigitgulyurt.net.tr'
    STREAM_KEY = os.environ.get('STREAM_KEY') or ''
    STREAM_LIVE_FALLBACK = os.environ.get('STREAM_LIVE_FALLBACK', 'false')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

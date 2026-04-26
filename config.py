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
    SHOW_STREAM_SECTION = os.environ.get('SHOW_STREAM_SECTION', 'false').lower() == 'true'
    STREAM_LIVE_FALLBACK = os.environ.get('STREAM_LIVE_FALLBACK', 'false')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '').strip(' "\'')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip(' "\'')
    GOOGLE_REDIRECT_URI  = os.environ.get('GOOGLE_REDIRECT_URI',
                         'https://obsidian.yigitgulyurt.net.tr/oauth2callback').strip(' "\'')
    GOOGLE_TOKEN_PATH    = os.path.join(os.path.dirname(__file__), 'google_token.json')

    OBSIDIAN_PASSWORD = os.environ.get('OBSIDIAN_PASSWORD', '')
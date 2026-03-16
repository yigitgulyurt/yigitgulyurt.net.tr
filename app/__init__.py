from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'admin.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.routes.main import bp as main_bp
    from app.routes.projects import bp as projects_bp
    from app.routes.blog import bp as blog_bp
    from app.routes.contact import bp as contact_bp
    from app.routes.admin import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix='/projeler')
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(contact_bp, url_prefix='/iletisim')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    register_context_processors(app)

    return app

from app import models  # noqa


from datetime import datetime

def register_context_processors(app):
    @app.context_processor
    def inject_globals():
        from flask import current_app
        return {
            'now': datetime.utcnow(),
            'config': current_app.config,
        }

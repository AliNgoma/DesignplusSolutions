"""Flask extensions, instantiated here so models and blueprints can import
them without creating a circular dependency on the app factory."""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'admin.login'
login_manager.login_message = 'Please sign in to continue.'
login_manager.login_message_category = 'error'

"""
Flask extension singletons — imported by app factory and modules.
"""
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_session import Session
from flask_smorest import Api
from flask_wtf.csrf import CSRFProtect

bcrypt       = Bcrypt()
login_manager = LoginManager()
sess         = Session()
smorest_api  = Api()
csrf         = CSRFProtect()

login_manager.login_view       = "auth.login"
login_manager.login_message    = "Please log in to access TaskBoard."
login_manager.login_message_category = "info"

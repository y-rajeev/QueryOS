from flask import Flask
from flask_login import LoginManager, UserMixin
from dotenv import load_dotenv
import os

load_dotenv()

# Basic User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

def create_app():
    # Get the absolute path to the templates directory
    template_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'))
    
    # Create Flask app with explicit template folder
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')))
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'main.dashboard'
    
    @login_manager.user_loader
    def load_user(user_id):
        # For now, return a basic user
        return User(user_id)
    
    # Register blueprints
    from app.routes import main, data
    app.register_blueprint(main.bp)
    app.register_blueprint(data.bp, url_prefix='/data')
    
    return app 
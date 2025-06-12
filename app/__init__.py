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
    from app.routes import main, data, dispatch_reports, sales_order
    app.register_blueprint(main.bp)
    app.register_blueprint(data.bp, url_prefix='/data')
    app.register_blueprint(dispatch_reports.bp)
    app.register_blueprint(sales_order.bp)
    
    # Register custom Jinja2 filters
    @app.template_filter('number_format')
    def number_format(value):
        """Format numbers with commas as thousand separators."""
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return value
    
    return app 
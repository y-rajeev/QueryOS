from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    # Get the absolute path to the templates directory
    template_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'))
    
    # Create Flask app with explicit template folder
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')))
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # Register blueprints
    from app.routes import main, data
    app.register_blueprint(main.bp)
    app.register_blueprint(data.bp)
    
    return app 
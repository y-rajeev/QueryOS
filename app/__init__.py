from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # Register blueprints
    from app.routes import main, data
    app.register_blueprint(main.bp)
    app.register_blueprint(data.bp)
    
    return app 
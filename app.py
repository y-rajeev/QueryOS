from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv # Import load_dotenv
from app.routes import data
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

# Load environment variables from .env file
load_dotenv()

def create_app(test_config: Optional[dict] = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        test_config: Optional test configuration dictionary
        
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_mapping(
            SECRET_KEY=os.getenv('SECRET_KEY', 'dev'),
            DB_HOST=os.getenv('DB_HOST'),
            DB_NAME=os.getenv('DB_NAME'),
            DB_USER=os.getenv('DB_USER'),
            DB_PASSWORD=os.getenv('DB_PASSWORD'),
            DB_PORT=os.getenv('DB_PORT', '5432'),
            MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE='Lax',
        )

        # Explicitly check for required database environment variables
        # This check is now less critical as direct DB connection is being removed, 
        # but keeping it for now if other modules still rely on it temporarily.
        # required_db_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        # for var in required_db_vars:
        #     if not app.config.get(var):
        #         raise RuntimeError(f"Missing required environment variable: {var}. Please ensure your .env file is correctly configured.")

    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Initialize extensions
    csrf = CSRFProtect(app)
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/queryos.log',
                                         maxBytes=10240,
                                         backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('QueryOS startup')

    # Register blueprints
    app.register_blueprint(data.bp)

    # No more direct database teardown needed here as `database.py` is removed.

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) 
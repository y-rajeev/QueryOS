from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv # Import load_dotenv
from app import create_app
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

# Load environment variables from .env file
load_dotenv()

def create_app_with_extensions(test_config: Optional[dict] = None) -> Flask:
    """
    Create and configure the Flask application with extensions.
    
    Args:
        test_config: Optional test configuration dictionary
        
    Returns:
        Flask: Configured Flask application instance
    """
    app = create_app()
    
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

    # Register custom Jinja2 filters
    @app.template_filter('number_format')
    def number_format(value):
        """Format numbers with commas as thousand separators."""
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return value

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app_with_extensions()
    app.run(debug=True) 
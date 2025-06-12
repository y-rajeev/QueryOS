from flask import Flask, render_template, jsonify, request
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv # Import load_dotenv
from app import create_app
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional
import requests

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

    @app.route('/data/pending-order')
    def get_pending_order_json():
        # This route will now strictly return the JSON data.
        # In a real application, this data would typically be fetched from a database or another service.
        # For this example, I am using the sample JSON data you provided.
        json_data = {
          "data": [
            {
              "ETD": "2025-06-19",
              "channel_abb": "Amazon IN",
              "date": "2025-06-02",
              "dispatched_qty": 0,
              "mode": "Road",
              "pending_qty": 3818,
              "po_qty": 3818,
              "production": "Mumbai",
              "shipment_id": "EH1185-IN",
              "status": "In-Prod"
            },
            {
              "ETD": "2025-06-13",
              "channel_abb": "Amazon IN",
              "date": "2025-05-26",
              "dispatched_qty": 125,
              "mode": "Road",
              "pending_qty": 2353,
              "po_qty": 2478,
              "production": "Karur",
              "shipment_id": "EH2184-IN",
              "status": "In-Prod"
            },
            {
              "ETD": "2025-06-13",
              "channel_abb": "Amazon UK",
              "date": "2025-05-20",
              "dispatched_qty": 0,
              "mode": "Sea",
              "pending_qty": 2695,
              "po_qty": 2695,
              "production": "Karur",
              "shipment_id": "EH2181-UK",
              "status": "In-Prod"
            },
            {
              "ETD": "2025-06-20",
              "channel_abb": "Amazon EU",
              "date": "2025-05-20",
              "dispatched_qty": 0,
              "mode": "Sea",
              "pending_qty": 10253,
              "po_qty": 10253,
              "production": "Karur",
              "shipment_id": "EH2183-EU",
              "status": "In-Prod"
            },
            {
              "ETD": "2025-06-11",
              "channel_abb": "Amazon IN",
              "date": "2025-05-20",
              "dispatched_qty": 1833,
              "mode": "Road",
              "pending_qty": 951,
              "po_qty": 2677,
              "production": "Karur",
              "shipment_id": "EH2182-IN",
              "status": "In-Prod"
            },
            {
              "ETD": "2025-06-17",
              "channel_abb": "Amazon EU",
              "date": "2025-05-20",
              "dispatched_qty": 0,
              "mode": "Sea",
              "pending_qty": 5372,
              "po_qty": 5372,
              "production": "Mumbai",
              "shipment_id": "EH1184-EU",
              "status": "In-Prod"
            },
            {
              "ETD": "2025-06-17",
              "channel_abb": "Amazon UK",
              "date": "2025-05-14",
              "dispatched_qty": 0,
              "mode": "Sea",
              "pending_qty": 6727,
              "po_qty": 6727,
              "production": "Mumbai",
              "shipment_id": "EH1183-UK",
              "status": "In-Prod"
            },
            {
              "ETD": "2025-06-10",
              "channel_abb": "Amazon US",
              "date": "2025-05-13",
              "dispatched_qty": 4463,
              "mode": "Sea",
              "pending_qty": 3067,
              "po_qty": 7505,
              "production": "Mumbai",
              "shipment_id": "EH1181-USA",
              "status": "In-Prod"
            },
            {
              "ETD": "2025-06-11",
              "channel_abb": "Amazon IN",
              "date": "2025-05-13",
              "dispatched_qty": 0,
              "mode": "Road",
              "pending_qty": 6338,
              "po_qty": 6338,
              "production": "Mumbai",
              "shipment_id": "EH1182-IN",
              "status": "In-Prod"
            }
          ],
          "headers": [
            "shipment_id",
            "date",
            "ETD",
            "production",
            "channel_abb",
            "mode",
            "po_qty",
            "dispatched_qty",
            "pending_qty",
            "status"
          ],
          "recordsFiltered": 9,
          "recordsTotal": 9
        }
        return jsonify(json_data)

    @app.route('/pending-orders-table-view')
    def pending_orders_table_view():
        # Fetch data from the API endpoint
        api_url = 'http://127.0.0.1:5000/data/pending-order'
        try:
            response = requests.get(api_url)
            response.raise_for_status() # Raise an exception for HTTP errors
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from API: {e}")
            # Handle error gracefully, e.g., return an empty table or error message
            data = {"headers": [], "data": [], "recordsTotal": 0}

        # Pass the data to the template
        return render_template('shipment.html',
                             headers=data['headers'],
                             orders=data['data'],
                             total_records=data['recordsTotal'])

    return app

if __name__ == '__main__':
    app = create_app_with_extensions()
    app.run(debug=True) 
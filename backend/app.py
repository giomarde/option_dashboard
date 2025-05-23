"""
Main Flask app using the modular pricing framework.
"""

from flask import Flask
from flask_cors import CORS
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Set up data directory if it doesn't exist
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(data_dir, exist_ok=True)

# Initialize backend components
from init import initialize_backend
components = initialize_backend(app, data_dir)

# Make components available globally
data_provider = components['data_provider']
volatility_model = components['volatility_model']
option_processor = components['option_processor']

# Main entry point
if __name__ == '__main__':
    # Start the Flask app
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting application on port {port}")
    logger.info(f"Available models: Bachelier, Dempster (fallback), Miltersen (fallback)")
    logger.info(f"Data directory: {data_dir}")
    app.run(debug=True, host='0.0.0.0', port=port)
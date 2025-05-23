# backend/app.py
"""
Main Flask app - Simple version with hardcoded data path
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

# HARDCODED DATA PATH - From your original example
data_dir = r'C:\Users\GIOM\OneDrive - Equinor\Desktop\LNG\Prices'

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
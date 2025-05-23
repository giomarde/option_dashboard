# backend/init.py
"""
Integration initialization module - Updated with proper path handling.

This module sets up the connections between different components of the pricing system.
"""

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_backend(app_instance=None, data_folder=None):
    """
    Initialize the backend components.
    
    Args:
        app_instance: Optional Flask app instance
        data_folder: Path to the data folder (can be absolute or relative)
        
    Returns:
        Dictionary with initialized components
    """
    logger.info("Initializing backend components")
    
    # Determine data folder path
    if data_folder is None:
        # Default to 'data' folder in backend directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        data_folder = os.path.join(backend_dir, 'data')
    elif not os.path.isabs(data_folder):
        # If relative path provided, make it relative to backend directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        data_folder = os.path.join(backend_dir, data_folder)
    
    # Make sure the data folder exists
    os.makedirs(data_folder, exist_ok=True)
    logger.info(f"Using data folder: {data_folder}")
    
    # Initialize data provider
    from data_feed import get_data_provider
    data_provider = get_data_provider('csv', data_folder=data_folder)
    logger.info(f"Initialized data provider: CSV ({data_folder})")
    
    # Initialize volatility model
    from models.volatility import VolatilityModel
    volatility_model = VolatilityModel(data_provider)
    logger.info("Initialized volatility model")
    
    # Initialize option processor
    from processors import OptionProcessor
    option_processor = OptionProcessor(data_provider)
    logger.info("Initialized option processor")
    
    # Register API routes if app instance is provided
    if app_instance:
        register_api_routes(app_instance, option_processor, data_provider)
        logger.info("Registered API routes")
    
    # Return initialized components
    return {
        'data_provider': data_provider,
        'volatility_model': volatility_model,
        'option_processor': option_processor
    }

def register_api_routes(app, option_processor, data_provider):
    """
    Register API routes for the Flask app.
    
    Args:
        app: Flask app instance
        option_processor: Option processor instance
        data_provider: Data provider instance
    """
    from flask import request, jsonify
    
    @app.route('/api/pricing', methods=['POST'])
    def price_option():
        """
        Price an option based on the provided configuration from the frontend
        """
        try:
            # Get the configuration from the frontend
            config = request.json
            logger.info(f"Received pricing request: {config.get('deal_type')} option")
            
            # Process the request using the option processor
            results = option_processor.process(config)
            
            return jsonify(results)
            
        except Exception as e:
            logger.error(f"Error pricing option: {str(e)}", exc_info=True)
            return jsonify({"error": True, "message": f"Failed to price option: {str(e)}"}), 500
    
    @app.route('/api/market-data', methods=['GET'])
    def get_market_data():
        """
        Get market data for a specific index
        """
        try:
            index = request.args.get('index')
            date = request.args.get('date')  # Optional
            
            if not index:
                return jsonify({"error": True, "message": "Index parameter is required"}), 400
            
            # Get market data from our data provider
            market_data = data_provider.fetch_market_data(index, date)
            
            return jsonify(market_data)
            
        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}", exc_info=True)
            return jsonify({"error": True, "message": f"Failed to get market data: {str(e)}"}), 500
    
    @app.route('/api/volatility-surface', methods=['GET'])
    def get_volatility_surface():
        """
        Get volatility surface data for indices
        """
        try:
            primary_index = request.args.get('primary')
            secondary_index = request.args.get('secondary')
            date = request.args.get('date')
            
            if not primary_index:
                return jsonify({"error": True, "message": "Primary index parameter is required"}), 400
            
            # Initialize volatility model
            from models.volatility import VolatilityModel
            vol_model = VolatilityModel(data_provider)
            
            # Get base prices
            primary_data = data_provider.fetch_market_data(primary_index, date)
            base_prices = {primary_index: primary_data.get('price', 10.0)}
            
            if secondary_index:
                secondary_data = data_provider.fetch_market_data(secondary_index, date)
                base_prices[secondary_index] = secondary_data.get('price', 9.0)
                base_prices[f"{primary_index}-{secondary_index}"] = base_prices[primary_index] - base_prices[secondary_index]
            
            # Get volatility surface
            indices = [primary_index]
            if secondary_index:
                indices.append(secondary_index)
                
            # Use current date if not provided
            from datetime import datetime
            current_date = datetime.now()
            evaluation_date = date or current_date.strftime('%Y-%m-%d')
            
            # Assume delivery 3 months from now for the surface
            delivery_date = current_date.replace(month=current_date.month + 3)
            if delivery_date.month > 12:
                delivery_date = delivery_date.replace(year=delivery_date.year + 1, month=delivery_date.month - 12)
            
            volatility_surface = vol_model.get_volatility_surface(
                indices, evaluation_date, delivery_date, base_prices)
            
            return jsonify(volatility_surface)
            
        except Exception as e:
            logger.error(f"Error getting volatility surface: {str(e)}", exc_info=True)
            return jsonify({"error": True, "message": f"Failed to get volatility surface: {str(e)}"}), 500
    
    @app.route('/api/test/data-folder', methods=['GET'])
    def test_data_folder():
        """
        Test endpoint to check data folder configuration and contents
        """
        try:
            # Get data folder path from data provider
            data_folder_path = data_provider.data_folder
            
            # Check if folder exists
            folder_exists = os.path.exists(data_folder_path)
            
            # List CSV files if folder exists
            csv_files = []
            if folder_exists:
                csv_files = [f for f in os.listdir(data_folder_path) if f.endswith('.csv')]
            
            return jsonify({
                "data_folder": data_folder_path,
                "exists": folder_exists,
                "csv_files": csv_files,
                "file_count": len(csv_files)
            })
            
        except Exception as e:
            logger.error(f"Error testing data folder: {str(e)}", exc_info=True)
            return jsonify({"error": True, "message": f"Failed to test data folder: {str(e)}"}), 500
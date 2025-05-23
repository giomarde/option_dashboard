"""
Integration initialization module.

This module sets up the connections between different components of the pricing system.
"""

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_backend(app_instance=None, data_folder='data'):
    """
    Initialize the backend components.
    
    Args:
        app_instance: Optional Flask app instance
        data_folder: Path to the data folder
        
    Returns:
        Dictionary with initialized components
    """
    logger.info("Initializing backend components")
    
    # Make sure the data folder exists
    os.makedirs(data_folder, exist_ok=True)
    
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
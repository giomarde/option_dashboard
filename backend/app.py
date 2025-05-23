"""
Main API entry point for the option pricing backend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from datetime import datetime

# Import our data feed module
from data_feed import get_data_provider

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create a data provider instance
data_provider = get_data_provider('csv', data_folder='data')

@app.route('/api/pricing', methods=['POST'])
def price_option():
    """
    Price an option based on the provided configuration from the frontend
    """
    try:
        # Get the configuration from the frontend
        config = request.json
        logger.info(f"Received pricing request: {config.get('deal_type')} option")
        
        # Extract the indices from the config
        primary_index = config.get('primary_index')
        secondary_index = config.get('secondary_index')
        
        if not primary_index or not secondary_index:
            return jsonify({"error": True, "message": "Primary and secondary indices are required"}), 400
        
        # Get current date for pricing (or use evaluation_date from config)
        pricing_date = config.get('evaluation_date', datetime.now().strftime('%Y-%m-%d'))
        
        # 1. FETCH MARKET DATA
        # This gets current prices for the selected indices
        logger.info(f"Fetching market data for {primary_index} and {secondary_index}")
        primary_data = data_provider.fetch_market_data(primary_index, pricing_date)
        secondary_data = data_provider.fetch_market_data(secondary_index, pricing_date)
        
        # 2. FETCH FORWARD CURVES
        # This gets forward curves for future delivery months
        logger.info(f"Fetching forward curves")
        primary_curve = data_provider.fetch_forward_curve(primary_index, pricing_date)
        secondary_curve = data_provider.fetch_forward_curve(secondary_index, pricing_date)
        
        # 3. FETCH VOLATILITY DATA
        # This gets volatility information needed for option pricing
        logger.info(f"Fetching volatility data")
        vol_data = data_provider.fetch_volatility_surface(primary_index, secondary_index, pricing_date)
        
        # 4. CALCULATE OPTION VALUE
        # This is where you'd call your actual pricing models
        # For now, we'll just return the market data we've collected
        
        # Mock calculation for demonstration
        primary_price = primary_data.get('price', 0)
        secondary_price = secondary_data.get('price', 0)
        spread = primary_price - secondary_price
        
        # Simple calculation (just for demonstration)
        strike = config.get('secondary_differential', 0) - config.get('primary_differential', 0) + config.get('total_cost_per_option', 0)
        time_factor = 0.5  # Placeholder - calculate from dates
        delta = 0.7 if spread > strike else 0.3
        option_value = abs(spread - strike) * delta * time_factor
        
        # Format the option date for the response
        option_date = f"{config.get('first_delivery_year', 2025)}-{config.get('first_delivery_month', 'Jan')}-{config.get('delivery_day', 1)}"
        
        # Prepare the response with all the pricing results
        result = {
            "total_value": option_value,
            "option_values": {
                option_date: option_value
            },
            "portfolio_greeks": {
                "delta": delta,
                "gamma": 1.63,
                "vega": 0.14,
                "theta": -0.11
            },
            "forward_spreads": [spread],
            "volatilities": [vol_data.get('primary', [{}])[0].get('volatility', 0.3)],
            # Include market data for debugging
            "market_data": {
                primary_index: primary_data,
                secondary_index: secondary_data
            }
        }
        
        # Add Monte Carlo results if requested
        if config.get('run_monte_carlo', False):
            result["mc_results"] = {
                "summary_statistics": {
                    "mean": option_value,
                    "std": option_value * 0.2,
                    "percentiles": {
                        "5": option_value * 0.5,
                        "25": option_value * 0.8,
                        "50": option_value,
                        "75": option_value * 1.2,
                        "95": option_value * 1.5
                    }
                },
                "exercise_statistics": {
                    "exercise_probabilities": [{
                        "primary": delta,
                        "secondary": 1 - delta
                    }]
                }
            }
        
        return jsonify(result)
        
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

# Main entry point
if __name__ == '__main__':
    # Set up data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if not os.path.exists(data_dir):
        logger.info(f"Creating data directory: {data_dir}")
        os.makedirs(data_dir)

    # Start the Flask app
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting application on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
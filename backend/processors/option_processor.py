"""
Option Processor Framework

A modular framework for processing option pricing requests with different pricing models.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Union, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptionProcessor:
    """
    General processor for option pricing requests that can work with any pricing model.
    """
    
    def __init__(self, data_provider=None):
        """
        Initialize the option processor.
        
        Args:
            data_provider: Optional data provider instance
        """
        self.data_provider = data_provider
        self.last_results = None
    
    def process(self, config: Dict[str, any], market_data: Optional[Dict] = None) -> Dict[str, any]:
        """
        Process an option pricing request using the specified model.
        
        Args:
            config: Dictionary with configuration parameters
            market_data: Optional pre-fetched market data
            
        Returns:
            Dictionary with pricing results
        """
        logger.info(f"Processing option pricing request for {config.get('option_type')} option")
        
        # 1. PREPARE MARKET DATA
        if market_data is None:
            market_data = self._fetch_market_data(config)
            
        # 2. INITIALIZE PRICING MODEL
        model = self._get_pricing_model(config, market_data)
        
        # 3. EXECUTE PRICING
        results = model.process(market_data)
        
        # 4. POST-PROCESS RESULTS
        post_processed = self._post_process_results(results, config, market_data)
        
        self.last_results = post_processed
        return post_processed
    
    def _fetch_market_data(self, config: Dict[str, any]) -> Dict[str, any]:
        """
        Fetch all required market data for the pricing model with improved error handling.
        
        Args:
            config: Dictionary with configuration parameters
            
        Returns:
            Dictionary with market data
        """
        # Extract relevant parameters
        primary_index = config.get('primary_index')
        secondary_index = config.get('secondary_index')
        option_type = config.get('option_type')
        evaluation_date_str = config.get('evaluation_date')

        # Create pricing_date (today) for market data fetching
        pricing_date = datetime.now()
        pricing_date_str = pricing_date.strftime('%Y-%m-%d')
        
        # Build list of indices to fetch
        indices = [primary_index]
        if secondary_index and secondary_index != primary_index:
            indices.append(secondary_index)
            
        # Add basket indices if applicable
        basket_indices = config.get('basket_indices', [])
        for idx in basket_indices:
            if idx not in indices:
                indices.append(idx)
        
        # Parse evaluation date
        if isinstance(evaluation_date_str, str):
            evaluation_date = datetime.strptime(evaluation_date_str, '%Y-%m-%d')
        else:
            evaluation_date = evaluation_date_str or datetime.now()
            
        # Calculate delivery dates
        delivery_dates = self._calculate_delivery_dates(config)
        
        # Initialize result structure
        market_data = {
            'evaluation_date': evaluation_date,
            'delivery_dates': delivery_dates,
            'indices_data': {},
            'forward_curves': {},
            'volatilities': {},
            'forward_spreads': [],
            'spread_volatilities': []  # Ensure this is initialized
        }
        
        # Fetch data for each index if data provider is available
        if self.data_provider:
            for index in indices:
                try:
                    # 1. Get current price data
                    current_data = self.data_provider.fetch_market_data(
                        index, pricing_date_str)
                    market_data['indices_data'][index] = current_data
                    
                    # 2. Get forward curve
                    forward_curve = self.data_provider.fetch_forward_curve(
                        index, 12, pricing_date_str)
                    market_data['forward_curves'][index] = forward_curve
                except Exception as e:
                    logger.error(f"Error fetching data for {index}: {e}")
                    # Use placeholders if data fetching fails
                    market_data['indices_data'][index] = {'price': 10.0, 'lastUpdated': str(evaluation_date)}
                    market_data['forward_curves'][index] = pd.DataFrame(
                        {f"M{i:02d}": [10.0 + i*0.1] for i in range(1, 13)},
                        index=[pricing_date_str or str(evaluation_date)]
                    )
        else:
            # Create mock data if no data provider is available
            logger.warning("No data provider available, using mock data")
            for index in indices:
                market_data['indices_data'][index] = {'price': 10.0, 'lastUpdated': str(evaluation_date)}
                market_data['forward_curves'][index] = pd.DataFrame(
                    {f"M{i:02d}": [10.0 + i*0.1] for i in range(1, 13)},
                    index=[pricing_date_str or str(evaluation_date)]
                )
        
        # Calculate spreads if needed
        if option_type.startswith('vanilla_spread') and primary_index and secondary_index:
            # For each delivery date, calculate the spread
            for i, delivery_date in enumerate(delivery_dates):
                # Calculate months ahead
                months_ahead = (delivery_date.year - evaluation_date.year) * 12 + (delivery_date.month - evaluation_date.month)
                month_code = f"M{months_ahead+1:02d}"  # +1 because M01 is first month
                
                # Get forward prices with proper defaults
                primary_price = self._get_forward_price(market_data['forward_curves'][primary_index], month_code)
                secondary_price = self._get_forward_price(market_data['forward_curves'][secondary_index], month_code)
                
                # Ensure we don't have zero values
                if primary_price == 0:
                    primary_price = 10.0
                if secondary_price == 0:
                    secondary_price = 9.0
                    
                # Calculate spread
                spread = primary_price - secondary_price
                market_data['forward_spreads'].append(spread)
        
        # Handle volatility calculation with robust error handling
        try:
            from models.volatility import VolatilityModel
            vol_model = VolatilityModel(self.data_provider)
            
            # For spread options, we need volatility for the spread
            if delivery_dates:
                # Initialize with default volatilities
                market_data['spread_volatilities'] = [0.35] * len(delivery_dates)
                
                try:
                    # Generate volatility surfaces - wrap in try/except to catch any errors
                    vol_surface = vol_model.get_volatility_surface(
                        indices, evaluation_date, delivery_dates[0],
                        {idx: data.get('price', 10.0) for idx, data in market_data['indices_data'].items()}
                    )
                    market_data['volatilities'] = vol_surface
                    
                    # Extract volatilities for each delivery date
                    if option_type.startswith('vanilla_spread') and primary_index and secondary_index:
                        spread_key = f"{primary_index}-{secondary_index}"
                        if spread_key in vol_surface and vol_surface[spread_key]:
                            # Find ATM volatility
                            if market_data['forward_spreads']:
                                spread_val = market_data['forward_spreads'][0]
                                # Default to first vol point
                                closest_vol = vol_surface[spread_key][0]['volatility']  
                                
                                for vol_point in vol_surface[spread_key]:
                                    if abs(vol_point['strike'] - spread_val) < abs(closest_vol['strike'] - spread_val):
                                        closest_vol = vol_point['volatility']
                                
                                market_data['spread_volatilities'] = [closest_vol] * len(delivery_dates)
                            else:
                                # If no forward spreads, use the middle volatility
                                middle_idx = len(vol_surface[spread_key]) // 2
                                market_data['spread_volatilities'] = [vol_surface[spread_key][middle_idx]['volatility']] * len(delivery_dates)
                except Exception as e:
                    logger.error(f"Error generating volatility surface: {e}")
                    # Fallback to default volatilities already initialized
        except Exception as e:
            logger.error(f"Major error in volatility calculation: {e}")
            # Ensure we have default volatilities
            market_data['volatilities'] = {}
            market_data['spread_volatilities'] = [0.35] * len(delivery_dates)
            
            # Add placeholder volatility smiles
            for index in indices:
                market_data['volatilities'][index] = [
                    {"strike": 9.0, "volatility": 0.33},
                    {"strike": 9.5, "volatility": 0.31},
                    {"strike": 10.0, "volatility": 0.30},
                    {"strike": 10.5, "volatility": 0.31},
                    {"strike": 11.0, "volatility": 0.33}
                ]
            
            if primary_index and secondary_index:
                spread_key = f"{primary_index}-{secondary_index}"
                market_data['volatilities'][spread_key] = [
                    {"strike": -1.0, "volatility": 0.38},
                    {"strike": -0.5, "volatility": 0.36},
                    {"strike": 0.0, "volatility": 0.35},
                    {"strike": 0.5, "volatility": 0.36},
                    {"strike": 1.0, "volatility": 0.38}
                ]
        
        return market_data
    
    def _get_forward_price(self, forward_curve: pd.DataFrame, month_code: str) -> float:
        """
        Get forward price from forward curve.
        
        Args:
            forward_curve: Forward curve dataframe
            month_code: Month code (e.g., M01, M02)
            
        Returns:
            Forward price
        """
        default_price = 10.0  # Default placeholder
        
        if forward_curve is None or forward_curve.empty:
            return default_price
                
        if month_code in forward_curve.columns:
            price = forward_curve.iloc[0][month_code]
            if pd.notna(price) and price != 0:
                return price
                    
        # If month code not found or price is NaN or zero, try to find the closest month
        valid_months = [col for col in forward_curve.columns if col.startswith('M') and pd.notna(forward_curve.iloc[0][col]) and forward_curve.iloc[0][col] != 0]
        if valid_months:
            # Sort by month number
            valid_months.sort(key=lambda x: int(x[1:]))
            
            # Try to get the closest month
            target_month = int(month_code[1:])
            closest_month = valid_months[0]
            min_diff = abs(int(closest_month[1:]) - target_month)
            
            for month in valid_months:
                diff = abs(int(month[1:]) - target_month)
                if diff < min_diff:
                    min_diff = diff
                    closest_month = month
                        
            return forward_curve.iloc[0][closest_month]
        
        # Fallback to default
        return default_price
    
    def _calculate_delivery_dates(self, config: Dict[str, any]) -> List[datetime]:
        """
        Calculate delivery dates based on configuration.
        
        Args:
            config: Dictionary with configuration parameters
            
        Returns:
            List of delivery dates
        """
        delivery_dates = []
        
        # Parse first delivery month and year
        first_month = config.get('first_delivery_month', 'Jan')
        first_year = config.get('first_delivery_year', datetime.now().year)
        delivery_day = config.get('delivery_day', 1)
        
        # Convert month name to number
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        first_month_num = month_names.index(first_month) + 1
        
        # Get frequency and number of options
        num_options = config.get('num_options', 1)
        frequency = config.get('frequency', 'monthly')
        
        # Map frequency to month offset
        freq_map = {
            'single': 0,  # Special case, handled below
            'weekly': 0.25,
            'biweekly': 0.5,
            'monthly': 1,
            'quarterly': 3,
            'semiannual': 6,
            'annual': 12
        }
        
        month_offset = freq_map.get(frequency, 1)
        
        # Special case for single option
        if frequency == 'single' or num_options == 1:
            try:
                delivery_date = datetime(first_year, first_month_num, delivery_day)
                delivery_dates.append(delivery_date)
            except ValueError:
                # Handle invalid dates (e.g., Feb 30)
                last_day = self._get_last_day_of_month(first_year, first_month_num)
                delivery_date = datetime(first_year, first_month_num, min(delivery_day, last_day))
                delivery_dates.append(delivery_date)
            return delivery_dates
        
        # Generate dates for multiple options
        for i in range(num_options):
            # Calculate target month and year
            month_number = first_month_num + int(i * month_offset)
            year_offset = (month_number - 1) // 12
            month_number = ((month_number - 1) % 12) + 1
            target_year = first_year + year_offset
            
            try:
                delivery_date = datetime(target_year, month_number, delivery_day)
                delivery_dates.append(delivery_date)
            except ValueError:
                # Handle invalid dates (e.g., Feb 30)
                last_day = self._get_last_day_of_month(target_year, month_number)
                delivery_date = datetime(target_year, month_number, min(delivery_day, last_day))
                delivery_dates.append(delivery_date)
        
        return delivery_dates
    
    def _get_last_day_of_month(self, year: int, month: int) -> int:
        """
        Get the last day of a month.
        
        Args:
            year: Year
            month: Month
            
        Returns:
            Last day of the month
        """
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        last_day = (next_month - timedelta(days=1)).day
        return last_day
    
    def _get_pricing_model(self, config: Dict[str, any], market_data: Dict[str, any]):
        """
        Get the appropriate pricing model based on configuration.
        
        Args:
            config: Dictionary with configuration parameters
            market_data: Dictionary with market data
            
        Returns:
            Pricing model instance
        """
        # Import here to avoid circular imports
        from models import get_pricing_model
        
        # Update config with market data if needed
        config_copy = config.copy()
        config_copy['data_provider'] = self.data_provider
        
        # Get model instance
        return get_pricing_model(config_copy)
    
    def _post_process_results(self, results: Dict[str, any], 
                             config: Dict[str, any], 
                             market_data: Dict[str, any]) -> Dict[str, any]:
        """
        Post-process pricing results for additional information.
        
        Args:
            results: Dictionary with pricing results
            config: Dictionary with configuration parameters
            market_data: Dictionary with market data
            
        Returns:
            Enhanced results dictionary
        """
        # Make a copy to avoid modifying the original
        enhanced = results.copy()
        
        # Add market data context
        enhanced['market_context'] = {
            'evaluation_date': market_data['evaluation_date'].strftime('%Y-%m-%d'),
            'primary_price': market_data['indices_data'].get(config['primary_index'], {}).get('price'),
            'secondary_price': market_data['indices_data'].get(config['secondary_index'], {}).get('price') 
                if config.get('secondary_index') else None,
            'forward_spreads': market_data.get('forward_spreads', []),
        }
        
        # Add volatility smiles for visualization
        if 'volatilities' in market_data:
            enhanced['volatility_smiles'] = market_data['volatilities']
        
        # Calculate total contract value
        cargo_volume = config.get('cargo_volume', 3750000)  # Default to typical cargo size
        enhanced['total_contract_value'] = enhanced.get('total_value', 0) * cargo_volume * config.get('num_options', 1)
        
        # Add strike price calculation
        enhanced['strike_price'] = config.get('secondary_differential', 0) - config.get('primary_differential', 0) + config.get('total_cost_per_option', 0)
        
        # Add configuration summary
        enhanced['config_summary'] = {
            'option_type': config.get('option_type'),
            'pricing_model': config.get('pricing_model'),
            'primary_index': config.get('primary_index'),
            'secondary_index': config.get('secondary_index'),
            'cargo_volume': cargo_volume,
            'num_options': config.get('num_options', 1)
        }
        
        return enhanced
# backend/models/volatility/vol_model.py

from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Union, Tuple
import numpy as np
import pandas as pd
from scipy.stats import norm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VolatilityModel:
    """
    Volatility model using Heston stochastic volatility.
    """
    
    def __init__(self, data_provider=None):
        """
        Initialize the volatility model.
        
        Args:
            data_provider: Optional data provider instance
        """
        self.data_provider = data_provider
        
        # Default volatilities to use when historical data is not available
        self.default_volatilities = {
            'THE': 0.35,
            'TFU': 0.32,
            'JKM': 0.40,
            'DES': 0.38,
            'NBP': 0.33,
            'HH': 0.45,
        }
        
        # Default Heston parameters for different indices
        self.default_heston_params = {
            'default': {
                'v0': 0.04,      # Initial variance
                'kappa': 1.5,    # Mean reversion speed
                'theta': 0.04,   # Long-run variance
                'sigma': 0.3,    # Vol of vol
                'rho': -0.7      # Correlation
            },
            'THE': {
                'v0': 0.05,
                'kappa': 1.2,
                'theta': 0.05,
                'sigma': 0.35,
                'rho': -0.65
            },
            'TFU': {
                'v0': 0.04,
                'kappa': 1.3,
                'theta': 0.04,
                'sigma': 0.3,
                'rho': -0.7
            }
        }
    
    def calculate_volatility(self, indices: List[str], 
                            evaluation_date: Union[str, datetime],
                            delivery_date: Union[str, datetime],
                            historical_length: int = 365,
                            forward_curves: Optional[Dict] = None) -> Dict[str, Union[float, Dict]]:
        """
        Calculate volatilities for multiple indices and their spreads.
        
        Args:
            indices: List of index names
            evaluation_date: Evaluation date
            delivery_date: Delivery date
            historical_length: Days of historical data to use
            forward_curves: Optional dictionary with forward curves
                
        Returns:
            Dict containing volatilities for all indices and their spreads
        """
        # Convert dates if needed
        if isinstance(evaluation_date, str):
            evaluation_date = datetime.strptime(evaluation_date, '%Y-%m-%d')
        if isinstance(delivery_date, str):
            delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d')
        
        # Calculate time to delivery in years
        days_to_delivery = max(1, (delivery_date - evaluation_date).days)
        time_to_maturity = days_to_delivery / 365.0
        
        # Calculate historical start date
        historical_start = evaluation_date - timedelta(days=historical_length)
        
        # Fetch historical data for all indices
        historical_data = {}
        for index in indices:
            try:
                if self.data_provider:
                    # Format dates for data provider
                    start_date_str = historical_start.strftime('%Y-%m-%d')
                    end_date_str = evaluation_date.strftime('%Y-%m-%d')
                    
                    # Fetch historical data
                    historical_data[index] = self.data_provider.fetch_data(
                        index, start_date_str, end_date_str)
                else:
                    # Mock data if no provider
                    logger.warning(f"No data provider available, using mock data for {index}")
                    dates = pd.date_range(start=historical_start, end=evaluation_date)
                    historical_data[index] = pd.Series(
                        np.random.normal(10, 0.5, len(dates)), index=dates)
            except Exception as e:
                logger.error(f"Error fetching historical data for {index}: {e}")
                # Create mock data
                dates = pd.date_range(start=historical_start, end=evaluation_date)
                historical_data[index] = pd.Series(
                    np.random.normal(10, 0.5, len(dates)), index=dates)
        
        # Calculate individual volatilities and Heston parameters
        individual_vols = {}
        heston_params = {}
        
        for index in indices:
            # Calculate historical volatility first
            vol = self.estimate_volatility_from_historical_data(historical_data[index])
            individual_vols[index] = vol
            
            # Calibrate Heston parameters based on historical data
            params = self.calibrate_heston_parameters(index, vol, time_to_maturity)
            heston_params[index] = params
        
        # Calculate spread volatilities and parameters
        spread_vols = {}
        spread_heston_params = {}
        
        if len(indices) > 1:
            for i, index1 in enumerate(indices):
                for j, index2 in enumerate(indices):
                    if i < j:  # Avoid duplicate pairs and self-pairs
                        spread_name = f"{index1}-{index2}"
                        
                        try:
                            # Align the series on matching dates
                            aligned_data = pd.DataFrame({
                                'asset1': historical_data[index1],
                                'asset2': historical_data[index2]
                            }).dropna()
                            
                            # Calculate the spread series
                            spread_series = aligned_data['asset1'] - aligned_data['asset2']
                            
                            # Calculate volatility of the spread
                            spread_vol = self.estimate_volatility_from_historical_data(spread_series)
                            spread_vols[spread_name] = spread_vol
                            
                            # Calculate correlation between the two assets
                            correlation = aligned_data['asset1'].corr(aligned_data['asset2'])
                            
                            # Calibrate Heston parameters for the spread
                            spread_params = self.calibrate_spread_heston_parameters(
                                index1, index2, spread_vol, correlation, heston_params, time_to_maturity)
                            
                            spread_heston_params[spread_name] = spread_params
                            
                        except Exception as e:
                            logger.error(f"Error calculating spread vol for {spread_name}: {e}")
                            # Use a simple approximation based on individual vols
                            vol1 = individual_vols[index1]
                            vol2 = individual_vols[index2]
                            # Assume correlation of 0.5 as fallback
                            corr = 0.5
                            spread_vol = np.sqrt(vol1**2 + vol2**2 - 2 * corr * vol1 * vol2)
                            spread_vols[spread_name] = spread_vol
                            
                            # Use default spread Heston parameters
                            spread_heston_params[spread_name] = self.default_heston_params['default']
        
        return {
            'individual': individual_vols,
            'spreads': spread_vols,
            'heston_params': heston_params,
            'spread_heston_params': spread_heston_params,
            'time_to_maturity': time_to_maturity
        }
    
    def estimate_volatility_from_historical_data(self, price_series: pd.Series) -> float:
        """
        Calculate historical volatility from price series.
        
        Args:
            price_series: Historical price series
            
        Returns:
            float: Estimated annualized volatility
        """
        # Ensure data is sorted chronologically
        price_series = price_series.sort_index()
        
        # For normal model, use absolute price changes
        price_changes = price_series.diff().dropna()
        
        # Calculate daily volatility (standard deviation of changes)
        daily_vol = price_changes.std()
        
        # Annualize (assuming 252 trading days)
        annualized_vol = daily_vol * np.sqrt(252)
        
        # Ensure minimum volatility
        return max(0.01, annualized_vol)
    
    def calibrate_heston_parameters(self, index, base_vol, time_to_maturity):
        """
        Calibrate Heston model parameters based on the index and base volatility.
        """
        print(f"DEBUG - calibrate_heston_parameters for {index}: base_vol={base_vol}, time={time_to_maturity}")
        
        # Get default parameters for this index or use general defaults
        default_params = self.default_heston_params.get(index, self.default_heston_params['default'])
        print(f"DEBUG - Default params for {index}: {default_params}")
        
        # Convert normal vol to percentage vol for Heston model
        # This is critical - check if we're using the correct value for conversion
        avg_price = 10.0  # This is a placeholder, ideally we'd use actual average price
        percentage_vol = base_vol / avg_price
        print(f"DEBUG - Converting normal vol {base_vol} to percentage vol: {percentage_vol} (using avg_price={avg_price})")
        
        # Initial variance (v0) is square of percentage volatility
        v0 = percentage_vol**2
        
        # Set long-run variance (theta) to match initial variance
        theta = v0
        
        # Adjust vol-of-vol (sigma) based on historical vol level
        sigma = default_params['sigma'] * np.sqrt(v0 / max(0.01, default_params['v0']))
        
        # Set negative correlation parameter (rho) for downside skew
        rho = default_params['rho']
        
        # Adjust mean reversion speed (kappa) based on time to maturity
        kappa = default_params['kappa']
        
        result = {
            'v0': v0,
            'kappa': kappa,
            'theta': theta,
            'sigma': sigma,
            'rho': rho
        }
        
        print(f"DEBUG - Calibrated Heston params for {index}: {result}")
        
        return result
    
    def get_volatility_surface(self, indices: List[str],
                            evaluation_date: Union[str, datetime],
                            delivery_date: Union[str, datetime],
                            base_prices: Optional[Dict[str, float]] = None,
                            option_strikes: Optional[Dict[str, float]] = None,
                            option_type: str = "call",
                            time_to_maturity: Optional[float] = None,
                            forward_curves: Optional[Dict] = None) -> Dict[str, List[Dict[str, float]]]:
        """
        Generate complete volatility surface data for indices and spreads using Heston model.
        
        Improved approach:
        1. Get real historical data for each index and calculate historical volatility
        2. Use forward values from market data
        3. Generate dense grid of prices around forward (±50%) with more points near ATM
        4. Calculate Heston volatility for each price point based on calibrated parameters
        5. Calculate deltas for each point
        6. Structure all data properly for frontend visualization
        """
        try:
            # Parse dates and calculate time to maturity if not provided
            if time_to_maturity is None:
                if isinstance(evaluation_date, str):
                    evaluation_date = datetime.strptime(evaluation_date, '%Y-%m-%d')
                if isinstance(delivery_date, str):
                    delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d')
                    
                days_to_delivery = max(1, (delivery_date - evaluation_date).days)
                time_to_maturity = days_to_delivery / 365.0
            
            time_to_maturity = max(0.01, time_to_maturity)
            logger.info(f"Generating volatility surface with time_to_maturity: {time_to_maturity} years")
            
            # Ensure we have base prices
            if base_prices is None:
                base_prices = {index: 10.0 for index in indices}
                logger.warning(f"No base prices provided, using defaults: {base_prices}")
            else:
                logger.info(f"Using provided base prices: {base_prices}")
            
            # Generate volatility smiles for each index and spread
            result = {}
            
            # Process individual indices first
            for index in indices:
                # Step 1: Get historical data and calculate base volatility
                historical_vol = self._get_historical_volatility(index, evaluation_date)
                logger.info(f"Historical volatility for {index}: {historical_vol:.4f}")
                
                # Step 2: Get forward value for the index
                forward_value = base_prices.get(index, 10.0)
                logger.info(f"Forward value for {index}: {forward_value:.4f}")
                
                # Step 3: Generate price range around forward (±50%)
                # Create more points (100 instead of 15) with concentration near ATM
                min_price = forward_value * 0.5
                max_price = forward_value * 1.5
                
                # Generate points with higher density near ATM
                # Use 100 points total
                price_points = self._generate_price_points(forward_value, min_price, max_price, 100)
                
                # Step 4: Calculate Heston parameters based on historical vol
                heston_params = self.calibrate_heston_parameters(index, historical_vol, time_to_maturity)
                
                # Step 5: Generate volatility smile data points
                smile_data = []
                for price in price_points:
                    # Calculate moneyness (K/F)
                    moneyness = price / forward_value
                    
                    # Calculate Heston implied vol (as percentage)
                    percentage_vol_decimal = self.heston_implied_vol(moneyness, time_to_maturity, heston_params, option_type)
                    
                    # Convert to normal vol
                    normal_vol = percentage_vol_decimal * abs(forward_value)
                    
                    # Calculate delta at this point
                    delta = self._calculate_bachelier_delta(forward_value, price, time_to_maturity, normal_vol, option_type)
                    
                    # Add data point to smile
                    smile_data.append({
                        'strike': float(price),
                        'volatility': float(normal_vol),
                        'percentage_vol': float(percentage_vol_decimal * 100),  # Convert to percentage
                        'delta': float(delta),
                        'relative_strike': float(((price / forward_value) - 1) * 100),  # Relative to forward in %
                        'time_to_maturity': float(time_to_maturity)
                    })
                
                # Sort by strike
                smile_data.sort(key=lambda x: x['strike'])
                logger.info(f"Generated {len(smile_data)} volatility points for {index}")
                
                # Store in result
                result[index] = smile_data
            
            # Process spreads
            if len(indices) > 1:
                for i, index1 in enumerate(indices):
                    for j, index2 in enumerate(indices):
                        if i < j:  # Avoid duplicate pairs
                            spread_name = f"{index1}-{index2}"
                            
                            # Step 1: Get historical data for spread
                            spread_vol = self._get_historical_spread_volatility(index1, index2, evaluation_date)
                            logger.info(f"Historical volatility for {spread_name}: {spread_vol:.4f}")
                            
                            # Step 2: Get forward value for spread
                            spread_forward = base_prices.get(spread_name, 
                                                            base_prices.get(index1, 10.0) - 
                                                            base_prices.get(index2, 9.0))
                            logger.info(f"Forward spread value for {spread_name}: {spread_forward:.4f}")
                            
                            # Step 3: Treat spread exactly like an individual time series
                            # Use the same calibration method as for individual indices
                            heston_params = self.calibrate_heston_parameters(spread_name, spread_vol, time_to_maturity)
                            
                            # Generate spread range with appropriate points
                            min_spread = min(0, spread_forward - abs(spread_forward))
                            max_spread = max(0, spread_forward + abs(spread_forward))
                            
                            # Ensure reasonable min/max bounds
                            if min_spread == max_spread:
                                min_spread = -1.0
                                max_spread = 1.0
                                
                            # Generate points with higher density near ATM and near 0
                            spread_points = self._generate_spread_points(spread_forward, min_spread, max_spread, 100)
                            
                            # Generate smile data points for spread
                            spread_smile = []
                            for spread in spread_points:
                                # For spread options, moneyness is relative to spread forward
                                if abs(spread_forward) < 0.001:
                                    # Special case for zero or near-zero forward
                                    moneyness = 1.0
                                else:
                                    moneyness = spread / spread_forward
                                
                                # Calculate Heston implied vol using the same method as individual indices
                                percentage_vol = self.heston_implied_vol(moneyness, time_to_maturity, heston_params, option_type)
                                
                                # Convert to normal vol
                                normal_vol = percentage_vol * abs(spread_forward)
                                
                                # Calculate delta
                                delta = self._calculate_bachelier_delta(spread_forward, spread, time_to_maturity, normal_vol, option_type)
                                
                                # Add data point to smile
                                spread_smile.append({
                                    'strike': float(spread),
                                    'volatility': float(normal_vol),
                                    'percentage_vol': float(percentage_vol * 100),  # Convert to percentage
                                    'delta': float(delta),
                                    'relative_strike': float(((spread / max(0.01, abs(spread_forward))) - 1) * 100),
                                    'time_to_maturity': float(time_to_maturity)
                                })
                            
                            # Sort by strike
                            spread_smile.sort(key=lambda x: x['strike'])
                            logger.info(f"Generated {len(spread_smile)} volatility points for {spread_name}")
                            
                            # Store in result
                            result[spread_name] = spread_smile
                            
                            # If we have an option strike, log the volatility at that point
                            if option_strikes and spread_name in option_strikes:
                                strike = option_strikes[spread_name]
                                # Find closest strike
                                closest_point = min(spread_smile, key=lambda x: abs(x['strike'] - strike))
                                logger.info(f"For strike {strike:.4f}, closest volatility point: {closest_point}")
            
            logger.info(f"Volatility surface generation complete with {len(result)} keys: {list(result.keys())}")
            return result
        
        except Exception as e:
            logger.error(f"Error generating volatility surface: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Return a minimal fallback surface
            return self._generate_fallback_volatility_surface(indices, base_prices)
    
    def _generate_price_points(self, forward, min_price, max_price, num_points=100):
        """
        Generate price points with higher density around ATM (forward value).
        
        Args:
            forward: Forward price
            min_price: Minimum price
            max_price: Maximum price
            num_points: Number of points to generate
            
        Returns:
            numpy array: Generated price points
        """
        # Create denser points near ATM
        # Use a combination of uniform and normal distributions
        
        # Uniform distribution for coverage across the entire range
        uniform_points = np.linspace(min_price, max_price, num_points // 2)
        
        # Normal distribution around ATM for higher density
        normal_std = (max_price - min_price) * 0.15  # 15% of range
        normal_points = np.random.normal(forward, normal_std, num_points // 2)
        normal_points = np.clip(normal_points, min_price, max_price)
        
        # Combine both distributions
        all_points = np.concatenate([uniform_points, normal_points])
        
        # Add key moneyness points
        for moneyness in [0.7, 0.8, 0.9, 0.95, 0.975, 0.99, 1.0, 1.01, 1.025, 1.05, 1.1, 1.2, 1.3]:
            all_points = np.append(all_points, forward * moneyness)
        
        # Add exact forward point
        all_points = np.append(all_points, forward)
        
        # Sort and remove duplicates
        result = np.sort(np.unique(all_points))
        
        return result
    
    def _generate_spread_points(self, forward, min_spread, max_spread, num_points=100):
        """
        Generate spread points with higher density around ATM and zero.
        
        Args:
            forward: Forward spread
            min_spread: Minimum spread
            max_spread: Maximum spread
            num_points: Number of points to generate
            
        Returns:
            numpy array: Generated spread points
        """
        # Create denser points near ATM and zero
        # Use a combination of uniform and two normal distributions
        
        # Uniform distribution for coverage across the entire range
        uniform_points = np.linspace(min_spread, max_spread, num_points // 3)
        
        # Normal distribution around ATM for higher density
        normal_std = (max_spread - min_spread) * 0.15  # 15% of range
        normal_points_atm = np.random.normal(forward, normal_std, num_points // 3)
        normal_points_atm = np.clip(normal_points_atm, min_spread, max_spread)
        
        # Normal distribution around zero for higher density (if zero is in range)
        if min_spread <= 0 and max_spread >= 0:
            normal_points_zero = np.random.normal(0, normal_std, num_points // 3)
            normal_points_zero = np.clip(normal_points_zero, min_spread, max_spread)
        else:
            normal_points_zero = np.array([])
        
        # Combine all distributions
        all_points = np.concatenate([uniform_points, normal_points_atm, normal_points_zero])
        
        # Add key relative points
        for rel in [-0.5, -0.25, -0.1, -0.05, 0, 0.05, 0.1, 0.25, 0.5]:
            point = forward * (1 + rel)
            if min_spread <= point <= max_spread:
                all_points = np.append(all_points, point)
        
        # Add exact forward point and zero
        all_points = np.append(all_points, forward)
        if min_spread <= 0 <= max_spread:
            all_points = np.append(all_points, 0)
        
        # Sort and remove duplicates
        result = np.sort(np.unique(all_points))
        
        return result
    
    def heston_implied_vol(self, moneyness, time_to_maturity, params, option_type="call"):
        """
        Calculate the implied volatility from the Heston model.
        """
        # For key moneyness values, print detailed debug info
        debug_this = abs(moneyness - 1.0) < 0.01 or abs(moneyness - 0.5) < 0.01 or abs(moneyness - 1.5) < 0.01
        
        if debug_this:
            print(f"DEBUG - heston_implied_vol: moneyness={moneyness}, time={time_to_maturity}, params={params}")
        
        # Ensure moneyness is valid
        if moneyness <= 0 or not np.isfinite(moneyness):
            print(f"WARNING - Invalid moneyness: {moneyness}, using default volatility")
            return 0.25  # Default reasonable volatility
        
        # Extract parameters
        v0 = params.get("v0", 0.04)
        kappa = params.get("kappa", 1.5)
        theta = params.get("theta", 0.04)
        sigma = params.get("sigma", 0.3)
        rho = params.get("rho", -0.7)
        
        # Calculate log-moneyness
        log_moneyness = np.log(moneyness)
        
        # Apply simplified Heston smile approximation
        atm_vol = np.sqrt(v0)
        skew_term = rho * sigma * np.sqrt(v0) / kappa
        curvature_term = (1 - rho**2) * sigma**2 * v0 / (2 * kappa**2)
        
        if debug_this:
            print(f"DEBUG - Calculation terms: atm_vol={atm_vol}, skew_term={skew_term}, curvature_term={curvature_term}")
            print(f"DEBUG - log_moneyness={log_moneyness}")
        
        # Apply the approximation (quadratic in log-moneyness)
        implied_vol = atm_vol * (1 + skew_term * log_moneyness + curvature_term * log_moneyness**2)
        
        # Ensure reasonable bounds
        implied_vol = max(0.01, min(implied_vol, 1.0))
        
        if debug_this:
            print(f"DEBUG - Final implied vol: {implied_vol}")
        
        return implied_vol
    
    def _calculate_bachelier_delta(self, forward, strike, time_to_maturity, volatility, option_type):
        """
        Calculate option delta using Bachelier model.
        
        Args:
            forward: Forward price
            strike: Strike price
            time_to_maturity: Time to maturity in years
            volatility: Volatility
            option_type: "call" or "put"
            
        Returns:
            float: Delta value
        """
        # Avoid division by zero
        if volatility <= 0 or time_to_maturity <= 0:
            # For at-the-money options
            if abs(forward - strike) < 0.0001:
                return 0.5 if option_type.lower() == 'call' else -0.5
            # For in-the-money calls
            elif forward > strike and option_type.lower() == 'call':
                return 1.0
            # For in-the-money puts
            elif forward < strike and option_type.lower() == 'put':
                return -1.0
            # For out-of-money calls
            elif forward < strike and option_type.lower() == 'call':
                return 0.0
            # For out-of-money puts
            else:
                return 0.0
        
        # Calculate d term for Bachelier model
        d = (forward - strike) / (volatility * np.sqrt(time_to_maturity))
        
        # Calculate delta
        if option_type.lower() == 'call':
            delta = norm.cdf(d)
        else:  # put
            delta = norm.cdf(d) - 1
        
        return delta
    
    def _get_historical_volatility(self, index, evaluation_date, days=90):
        """
        Get historical volatility from time series data.
        
        Args:
            index: Index name
            evaluation_date: Evaluation date
            days: Number of days of history to use
            
        Returns:
            float: Annualized volatility
        """
        try:
            if self.data_provider:
                # Calculate start date
                start_date = evaluation_date - timedelta(days=days)
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = evaluation_date.strftime('%Y-%m-%d')
                
                # Fetch historical data
                price_series = self.data_provider.fetch_data(index, start_date_str, end_date_str)
                
                # Calculate volatility
                vol = self.estimate_volatility_from_historical_data(price_series)
                return vol
            else:
                # If no data provider, use default volatility
                return self.default_volatilities.get(index, 0.35)
        except Exception as e:
            logger.warning(f"Failed to get historical volatility for {index}: {e}")
            return self.default_volatilities.get(index, 0.35)

    def _get_historical_spread_volatility(self, index1, index2, evaluation_date, days=90):
        """
        Get historical volatility for a spread between two indices.
        
        Args:
            index1: First index
            index2: Second index
            evaluation_date: Evaluation date
            days: Number of days of history to use
            
        Returns:
            float: Annualized spread volatility
        """
        try:
            if self.data_provider:
                # Calculate start date
                start_date = evaluation_date - timedelta(days=days)
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = evaluation_date.strftime('%Y-%m-%d')
                
                # Fetch historical data for both indices
                series1 = self.data_provider.fetch_data(index1, start_date_str, end_date_str)
                series2 = self.data_provider.fetch_data(index2, start_date_str, end_date_str)
                
                # Align on matching dates
                aligned_data = pd.DataFrame({
                    'index1': series1,
                    'index2': series2
                }).dropna()
                
                if len(aligned_data) < 5:
                    logger.warning(f"Insufficient aligned data for {index1}-{index2}, using fallback")
                    return max(0.3, (self.default_volatilities.get(index1, 0.35) + self.default_volatilities.get(index2, 0.35)) / 2)
                
                # Calculate spread series
                spread_series = aligned_data['index1'] - aligned_data['index2']
                
                # Calculate volatility
                vol = self.estimate_volatility_from_historical_data(spread_series)
                return vol
            else:
                # If no data provider, use default spread volatility
                return max(0.3, (self.default_volatilities.get(index1, 0.35) + self.default_volatilities.get(index2, 0.35)) / 2)
        except Exception as e:
            logger.warning(f"Failed to get historical spread volatility for {index1}-{index2}: {e}")
            return max(0.3, (self.default_volatilities.get(index1, 0.35) + self.default_volatilities.get(index2, 0.35)) / 2)

    def _calculate_correlation(self, index1, index2, evaluation_date, days=90):
        """
        Calculate correlation between two indices.
        
        Args:
            index1: First index
            index2: Second index
            evaluation_date: Evaluation date
            days: Number of days of history to use
            
        Returns:
            float: Correlation coefficient
        """
        try:
            if self.data_provider:
                # Calculate start date
                start_date = evaluation_date - timedelta(days=days)
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = evaluation_date.strftime('%Y-%m-%d')
                
                # Fetch historical data for both indices
                series1 = self.data_provider.fetch_data(index1, start_date_str, end_date_str)
                series2 = self.data_provider.fetch_data(index2, start_date_str, end_date_str)
                
                # Align on matching dates
                aligned_data = pd.DataFrame({
                    'index1': series1,
                    'index2': series2
                }).dropna()
                
                if len(aligned_data) < 5:
                    logger.warning(f"Insufficient aligned data for correlation of {index1}-{index2}, using fallback")
                    return 0.7  # Default high correlation for energy indices
                
                # Calculate correlation
                return aligned_data['index1'].corr(aligned_data['index2'])
            else:
                return 0.7  # Default correlation
        except Exception as e:
            logger.warning(f"Failed to calculate correlation for {index1}-{index2}: {e}")
            return 0.7  # Default correlation

    def _generate_fallback_volatility_surface(self, indices, base_prices):
        """
        Generate a fallback volatility surface when the main method fails.
        
        Args:
            indices: List of indices
            base_prices: Dictionary of base prices
            
        Returns:
            dict: Volatility surface data
        """
        result = {}
        
        # Generate simple volatility smiles for individual indices
        for index in indices:
            forward = base_prices.get(index, 10.0)
            vol = self.default_volatilities.get(index, 0.35)
            
            smile = []
            for i in range(7):
                strike = forward * (0.7 + i * 0.1)  # 70% to 130% of forward
                rel_strike = ((strike / forward) - 1) * 100
                normal_vol = vol * (1 + 0.1 * (rel_strike / 30)**2)  # Simple quadratic adjustment
                percentage_vol = (normal_vol / forward) * 100
                delta = self._calculate_bachelier_delta(forward, strike, 0.25, normal_vol, "call")
                
                smile.append({
                    'strike': float(strike),
                    'volatility': float(normal_vol),
                    'percentage_vol': float(percentage_vol),
                    'delta': float(delta),
                    'relative_strike': float(rel_strike),
                    'time_to_maturity': 0.25
                })
            
            result[index] = smile
        
        # Generate spread smiles if needed
        if len(indices) > 1:
            for i, index1 in enumerate(indices):
                for j, index2 in enumerate(indices):
                    if i < j:
                        spread_name = f"{index1}-{index2}"
                        spread_forward = base_prices.get(spread_name, 
                                                        base_prices.get(index1, 10.0) - 
                                                        base_prices.get(index2, 9.0))
                        
                        # Use higher volatility for spreads
                        spread_vol = max(0.3, 
                                        self.default_volatilities.get(index1, 0.35) + 
                                        self.default_volatilities.get(index2, 0.35)) / 1.5
                        
                        smile = []
                        min_spread = min(spread_forward * 0.5, 0)
                        max_spread = max(spread_forward * 1.5, 0)
                        if min_spread == max_spread:
                            min_spread = -1.0
                            max_spread = 1.0
                        
                        for i in range(7):
                            strike = min_spread + (max_spread - min_spread) * i / 6
                            rel_strike = ((strike / max(0.01, abs(spread_forward))) - 1) * 100
                            normal_vol = spread_vol * (1 + 0.1 * (rel_strike / 30)**2)
                            percentage_vol = (normal_vol / max(0.01, abs(spread_forward))) * 100
                            delta = self._calculate_bachelier_delta(spread_forward, strike, 0.25, normal_vol, "call")
                            
                            smile.append({
                                'strike': float(strike),
                                'volatility': float(normal_vol),
                                'percentage_vol': float(percentage_vol),
                                'delta': float(delta),
                                'relative_strike': float(rel_strike),
                                'time_to_maturity': 0.25
                            })
                        
                        result[spread_name] = smile
        
        logger.warning(f"Using fallback volatility surface with {len(result)} keys")
        return result
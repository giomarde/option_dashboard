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
        
        Args:
            index: Index name
            base_vol: Base ATM volatility (normal)
            time_to_maturity: Time to maturity in years
            
        Returns:
            Dict: Calibrated Heston parameters
        """
        # Get default parameters for this index or use general defaults
        default_params = self.default_heston_params.get(index, self.default_heston_params['default'])
        
        # Adjust v0 (initial variance) based on base volatility 
        # For normal vol, we need to convert to percentage vol for Heston
        # Assume average price of 10 for conversion
        avg_price = 10.0
        percentage_vol = base_vol / avg_price
        v0 = percentage_vol**2  # Initial variance is square of percentage volatility
        
        # Adjust long-run variance (theta) to match initial variance
        theta = v0
        
        # Higher vol usually means higher vol-of-vol
        sigma = default_params['sigma'] * np.sqrt(v0 / default_params['v0'])
        
        # Time to maturity affects skew
        rho = default_params['rho']
        if time_to_maturity < 0.25:
            rho = default_params['rho'] * 1.2  # More negative correlation for short-dated
        elif time_to_maturity > 1.0:
            rho = default_params['rho'] * 0.8  # Less negative correlation for long-dated
        
        # Keep mean reversion speed (kappa) from defaults
        kappa = default_params['kappa']
        
        return {
            'v0': v0,
            'kappa': kappa,
            'theta': theta,
            'sigma': sigma,
            'rho': rho
        }
    
    def calibrate_spread_heston_parameters(self, index1, index2, spread_vol, correlation, heston_params, time_to_maturity):
        """
        Calibrate Heston parameters for spread options based on individual assets.
        
        Args:
            index1: First index name
            index2: Second index name
            spread_vol: Volatility of the spread
            correlation: Correlation between the assets
            heston_params: Heston parameters for individual indices
            time_to_maturity: Time to maturity in years
            
        Returns:
            Dict: Calibrated spread Heston parameters
        """
        # Get Heston parameters for individual indices
        params1 = heston_params.get(index1, self.default_heston_params['default'])
        params2 = heston_params.get(index2, self.default_heston_params['default'])
        
        # Average price for conversion (placeholder, should use actual prices)
        avg_price = 10.0
        percentage_vol = spread_vol / avg_price
        
        # Initial variance based on spread vol
        v0 = percentage_vol**2
        
        # Long-run variance matches initial
        theta = v0
        
        # Mean reversion speed - average of individual assets
        kappa = (params1['kappa'] + params2['kappa']) / 2.0
        
        # Vol of vol - conservative approach using max
        sigma = max(params1['sigma'], params2['sigma'])
        
        # Correlation parameter - more negative for spreads
        base_rho = (params1['rho'] + params2['rho']) / 2.0
        # Adjust based on asset correlation
        if correlation > 0.7:
            # High positive correlation means more negative spread rho
            rho = base_rho * 1.2
        elif correlation < 0.3:
            # Low correlation means less negative spread rho
            rho = base_rho * 0.8
        else:
            rho = base_rho
        
        # Adjust rho based on time to maturity
        if time_to_maturity < 0.25:
            rho *= 1.2  # More pronounced skew for short-dated
        elif time_to_maturity > 1.0:
            rho *= 0.8  # Less pronounced skew for long-dated
        
        return {
            'v0': v0,
            'kappa': kappa,
            'theta': theta,
            'sigma': sigma,
            'rho': rho
        }
    
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
        
        Logical approach:
        1. Get time series data for each index and calculate historical volatility
        2. Pull forward values for the correct month
        3. Generate range of prices around forward (±50%)
        4. Calculate Heston volatility for each price point
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
                min_price = forward_value * 0.5
                max_price = forward_value * 1.5
                price_points = np.linspace(min_price, max_price, 100)
                logger.info(f"Generated {len(price_points)} price points from {min_price:.4f} to {max_price:.4f}")
                
                # Step 4: Calculate Heston parameters based on historical vol
                heston_params = self.calibrate_heston_parameters(index, historical_vol, time_to_maturity)
                logger.info(f"Calibrated Heston parameters for {index}: {heston_params}")
                
                # Step 5: Generate volatility smile data points
                smile_data = []
                for price in price_points:
                    # Calculate moneyness (K/F)
                    moneyness = price / forward_value
                    
                    # Calculate Heston implied vol (as percentage)
                    percentage_vol_decimal = self.heston_implied_vol(moneyness, time_to_maturity, heston_params, option_type)
                    
                    # Convert to normal vol
                    normal_vol = percentage_vol_decimal * abs(forward_value)  # Use abs to handle negative forwards
                    
                    # Calculate delta at this point
                    delta = self._calculate_bachelier_delta(forward_value, price, time_to_maturity, normal_vol, option_type)
                    
                    # Add data point to smile
                    smile_data.append({
                        'strike': float(price),
                        'volatility': float(normal_vol),
                        'percentage_vol': float((normal_vol / max(0.01, abs(price))) * 100),  # Calculate % relative to strike price
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
                            spread_forward = base_prices.get(spread_name, base_prices.get(index1, 10.0) - base_prices.get(index2, 9.0))
                            logger.info(f"Forward spread value for {spread_name}: {spread_forward:.4f}")
                            
                            # Step 3: Generate spread range (centered at forward, but ensure we include 0)
                            min_spread = min(spread_forward * 0.5, spread_forward - abs(spread_forward) * 0.5, 0)
                            max_spread = max(spread_forward * 1.5, spread_forward + abs(spread_forward) * 0.5, 0)
                            if min_spread == max_spread:
                                min_spread = -1.0
                                max_spread = 1.0
                            spread_points = np.linspace(min_spread, max_spread, 100)
                            logger.info(f"Generated {len(spread_points)} spread points from {min_spread:.4f} to {max_spread:.4f}")
                            
                            # Step 4: Calculate Heston parameters for spread
                            heston_params1 = self.calibrate_heston_parameters(index1, self._get_historical_volatility(index1, evaluation_date), time_to_maturity)
                            heston_params2 = self.calibrate_heston_parameters(index2, self._get_historical_volatility(index2, evaluation_date), time_to_maturity)
                            correlation = self._calculate_correlation(index1, index2, evaluation_date)
                            spread_heston_params = self.calibrate_spread_heston_parameters(
                                index1, index2, spread_vol, correlation, 
                                {index1: heston_params1, index2: heston_params2}, 
                                time_to_maturity
                            )
                            logger.info(f"Calibrated Heston parameters for {spread_name}: {spread_heston_params}")
                            
                            # Step 5: Generate volatility smile for spread
                            spread_smile = []
                            for spread in spread_points:
                                # For spread options, moneyness is relative to absolute spread value
                                # to handle cases where spread can be negative
                                moneyness = spread / max(0.01, abs(spread_forward))
                                if spread_forward < 0:
                                    moneyness = -moneyness  # Adjust sign for negative spreads
                                
                                # Calculate Heston implied vol
                                percentage_vol = self.heston_implied_vol(moneyness, time_to_maturity, spread_heston_params, option_type)
                                
                                # Convert to normal vol
                                normal_vol = percentage_vol * abs(spread_forward)
                                
                                # Calculate delta
                                delta = self._calculate_bachelier_delta(spread_forward, spread, time_to_maturity, normal_vol, option_type)
                                
                                # Add data point
                                spread_smile.append({
                                    'strike': float(spread),
                                    'volatility': float(normal_vol),
                                    'percentage_vol': float(percentage_vol * 100),  # Convert to percentage
                                    'delta': float(delta),
                                    'relative_strike': float(((spread / max(0.01, abs(spread_forward))) - 1) * 100),  # Relative to forward in %
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
    
    def generate_heston_smile(self, forward, base_vol, time_to_maturity, option_type, heston_params, center_strike=None, is_spread=False):
        """
        Generate volatility smile using the Heston model.
        
        Args:
            forward: Forward price
            base_vol: Base volatility (normal)
            time_to_maturity: Time to maturity in years
            option_type: "call" or "put"
            heston_params: Heston model parameters
            center_strike: Optional center strike
            is_spread: Whether this is a spread (affects strike range)
            
        Returns:
            List of volatility points
        """
        # Safety checks
        if forward == 0 or not np.isfinite(forward):
            forward = 1.0
        
        # Ensure reasonable base_vol (0.01 to 0.5 in normal vol terms)
        base_vol = min(max(0.01, base_vol), 0.5)
        
        # Default to forward if center_strike not provided
        if center_strike is None or not np.isfinite(center_strike) or center_strike == 0:
            center_strike = forward
        
        # Generate strikes around forward
        strikes = self._generate_strike_range(forward, center_strike, is_spread)
        
        # Create the smile
        smile = []
        
        # Debug log
        logger.debug(f"Generating Heston smile: forward={forward}, base_vol={base_vol}, time_to_maturity={time_to_maturity}")
        logger.debug(f"Heston params: {heston_params}")
        
        for strike in strikes:
            try:
                # Calculate moneyness
                moneyness = strike / forward if forward != 0 else 1.0
                
                # Calculate Heston implied volatility (as percentage vol)
                percentage_vol = self.heston_implied_vol(moneyness, time_to_maturity, heston_params, option_type)
                
                # Convert to normal vol
                normal_vol = percentage_vol * abs(forward)
                
                # Cap normal vol at 0.5 (reasonable maximum)
                normal_vol = min(normal_vol, 0.5)
                
                # Recalculate percentage vol for output
                percentage_vol_display = (normal_vol / max(0.01, abs(forward))) * 100
                
                # Calculate delta for this strike
                delta = self._calculate_bachelier_delta(forward, strike, time_to_maturity, normal_vol, option_type)
                
                # Determine if it's a key delta point
                is_key_delta = False
                for key_delta in [0.25, 0.5, 0.75]:
                    if abs(delta - key_delta) < 0.05:
                        is_key_delta = True
                        break
                
                # Create the volatility point
                smile.append({
                    'strike': float(strike),
                    'volatility': float(normal_vol),
                    'percentage_vol': float(percentage_vol_display),
                    'delta': float(delta),
                    'relative_strike': float((strike / forward - 1) * 100) if forward != 0 else 0.0,
                    'time_to_maturity': float(time_to_maturity),
                    'is_key_delta': is_key_delta
                })
            except Exception as e:
                logger.warning(f"Error calculating volatility for strike {strike}: {e}")
                # Skip this strike point or add a fallback
        
        # Ensure we have points at key deltas
        smile = self._ensure_key_delta_points(smile, forward, base_vol, time_to_maturity, option_type, heston_params)
        
        # Sort by strike
        smile.sort(key=lambda x: x['strike'])
        
        return smile
    
    def heston_implied_vol(self, moneyness, time_to_maturity, params, option_type="call"):
        """
        Calculate the implied volatility from the Heston model.
        
        Args:
            moneyness: Strike / Forward
            time_to_maturity: Time to maturity in years
            params: Heston parameters
            option_type: "call" or "put"
            
        Returns:
            float: Implied volatility (as decimal, not percentage)
        """
        # Ensure moneyness is valid and positive
        if moneyness <= 0 or not np.isfinite(moneyness):
            # For invalid moneyness, return a reasonable fallback
            return 0.25  # Default reasonable volatility
        
        # Extract parameters with safety checks
        v0 = min(params.get("v0", 0.04), 0.09)  # Cap at 0.09 (30% vol)
        kappa = max(params.get("kappa", 1.5), 0.5)
        theta = min(params.get("theta", 0.04), 0.09)  # Cap at 0.09 (30% vol)
        sigma = min(params.get("sigma", 0.3), 0.5)  # Cap vol of vol
        rho = max(min(params.get("rho", -0.7), 0.8), -0.8)  # Keep in [-0.8, 0.8]
        
        # Calculate log-moneyness with safety check
        log_moneyness = np.log(max(moneyness, 0.01))
        
        # Apply simplified Heston smile approximation based on moment matching
        # This is a 2nd order approximation based on expansion of the characteristic function
        
        # First moment (skew) - with limits to prevent extreme values
        skew_term = rho * sigma * v0 * time_to_maturity / max(kappa, 0.1)
        skew_term = max(-0.2, min(skew_term, 0.2))  # Limit skew effect
        
        # Second moment (curvature) - simplified approximation
        curvature_term = (1 - rho**2) * sigma**2 * v0 * time_to_maturity / (2 * max(kappa**2, 0.1))
        curvature_term = max(0, min(curvature_term, 0.1))  # Limit curvature effect
        
        # Apply the approximation
        atm_vol = np.sqrt(v0)  # ATM vol
        
        # Quadratic adjustment to vol based on log-moneyness
        adjustment = 1 + skew_term * log_moneyness + curvature_term * log_moneyness**2
        adjustment = max(0.5, min(adjustment, 1.5))  # Limit adjustment to [0.5, 1.5]
        
        implied_vol = atm_vol * adjustment
        
        # Ensure the vol is positive and within reasonable bounds (max 40% as percentage vol)
        implied_vol = max(0.01, min(implied_vol, 0.4))
        
        # Debug log
        logger.debug(f"Heston vol calculation: moneyness={moneyness}, T={time_to_maturity}, " 
                    f"params={params}, result={implied_vol}")
        
        return implied_vol
    
    def _generate_strike_range(self, forward, center_strike, is_spread=False):
        """
        Generate a reasonable range of strikes centered around forward and strike.
        
        Args:
            forward: Forward price
            center_strike: Center strike (option strike or forward)
            is_spread: Whether this is a spread (affects strike range)
            
        Returns:
            List of strike prices
        """
        # Safety check
        if forward == 0:
            forward = 1.0
        
        if is_spread:
            # For spreads: use range from 0 to 2*forward (or 2*forward to 0 if negative)
            if forward > 0:
                min_strike = 0
                max_strike = forward * 2
            else:
                min_strike = forward * 2
                max_strike = 0
                
            # Always include the option strike
            if center_strike < min_strike:
                min_strike = center_strike * 0.9
            elif center_strike > max_strike:
                max_strike = center_strike * 1.1
        else:
            # For indices: use ±50% range
            min_strike = forward * 0.5
            max_strike = forward * 1.5
            
            # Always include the option strike
            if center_strike < min_strike:
                min_strike = center_strike * 0.9
            elif center_strike > max_strike:
                max_strike = center_strike * 1.1
        
        # Generate 15 points including forward and center_strike
        num_points = 15
        
        # Create base linspace
        if min_strike == max_strike:
            # Edge case, single point
            base_strikes = np.array([min_strike])
        else:
            base_strikes = np.linspace(min_strike, max_strike, num_points)
        
        # Add forward and center_strike
        all_strikes = np.append(base_strikes, [forward, center_strike])
        
        # Sort and remove duplicates
        strikes = np.sort(np.unique(all_strikes))
        
        return strikes

    def _calculate_bachelier_delta(self, forward, strike, time_to_maturity, vol, option_type):
        """
        Calculate option delta using Bachelier model.
        
        Args:
            forward: Forward price
            strike: Strike price
            time_to_maturity: Time to maturity in years
            vol: Volatility
            option_type: "call" or "put"
            
        Returns:
            float: Delta value
        """
        # Avoid division by zero
        if vol <= 0 or time_to_maturity <= 0:
            # For at-the-money options
            if abs(forward - strike) < 0.0001:
                return 0.5
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
        d = (forward - strike) / (vol * np.sqrt(time_to_maturity))
        
        # Calculate delta
        if option_type.lower() == 'call':
            delta = norm.cdf(d)
        else:  # put
            delta = norm.cdf(d) - 1
        
        return delta

    def _ensure_key_delta_points(self, smile, forward, base_vol, time_to_maturity, option_type, heston_params=None):
        """
        Ensure that the smile contains points at key delta levels (0.25, 0.5, 0.75).
        
        Args:
            smile: Current smile
            forward: Forward price
            base_vol: Base volatility
            time_to_maturity: Time to maturity
            option_type: "call" or "put"
            heston_params: Optional Heston parameters
            
        Returns:
            Updated smile with key delta points
        """
        # Extract existing deltas
        existing_deltas = [point['delta'] for point in smile]
        
        # Key delta values to ensure
        key_deltas = [0.25, 0.5, 0.75]
        
        # Find which key deltas are missing
        missing_deltas = []
        for key_delta in key_deltas:
            if not any(abs(delta - key_delta) < 0.05 for delta in existing_deltas):
                missing_deltas.append(key_delta)
        
        # If we have all key deltas, return the original smile
        if not missing_deltas:
            return smile
        
        # Calculate strikes for missing key deltas
        for delta_target in missing_deltas:
            # Invert the delta function to find the corresponding strike
            strike = self._find_strike_for_delta(delta_target, forward, base_vol, time_to_maturity, option_type)
            
            # Calculate volatility at this strike using Heston model if available
            if heston_params:
                moneyness = strike / forward if forward != 0 else 1.0
                try:
                    percentage_vol = self.heston_implied_vol(moneyness, time_to_maturity, heston_params, option_type)
                except Exception:
                    # Fallback to simple smile approximation
                    moneyness_shift = moneyness - 1
                    percentage_vol = np.sqrt(heston_params['v0']) * (1 + 0.2 * moneyness_shift**2)
            else:
                # Simple approximation if Heston params not available
                moneyness = strike / forward - 1 if forward != 0 else 0
                vol_adjustment = 1.0 + 0.2 * moneyness**2
                percentage_vol = base_vol * vol_adjustment / max(0.01, abs(forward))
            
            # Convert to normal vol
            normal_vol = percentage_vol * abs(forward)
            normal_vol = min(max(0.01, normal_vol), 1.0)  # Reasonable bounds
            
            # Calculate percentage vol for output
            percentage_vol_output = (normal_vol / max(0.01, abs(forward))) * 100
            
            # Add the new point
            new_point = {
                'strike': float(strike),
                'volatility': float(normal_vol),
                'percentage_vol': float(percentage_vol_output),
                'delta': float(delta_target),
                'relative_strike': float((strike / forward - 1) * 100) if forward != 0 else 0.0,
                'time_to_maturity': float(time_to_maturity),
                'is_key_delta': True
            }
            
            smile.append(new_point)
        
        # Re-sort the smile by strike
        smile.sort(key=lambda x: x['strike'])
        
        return smile

    def _find_strike_for_delta(self, target_delta, forward, vol, time_to_maturity, option_type):
        """
        Find the strike that gives a specific delta.
        
        Args:
            target_delta: Target delta value
            forward: Forward price
            vol: Volatility
            time_to_maturity: Time to maturity
            option_type: "call" or "put"
            
        Returns:
            float: Strike price
        """
        # For Bachelier model, we can invert the delta formula directly
        
        # Adjust target delta for put options
        if option_type.lower() == 'put':
            effective_delta = target_delta + 1
        else:
            effective_delta = target_delta
        
        # Safety checks
        if not (0 <= effective_delta <= 1):
            effective_delta = max(0, min(1, effective_delta))
        
        # Invert the normal CDF to get the d value
        d = norm.ppf(effective_delta)
        
        # Solve for strike
        if time_to_maturity <= 0 or vol <= 0:
            # Edge case
            if effective_delta >= 0.5:
                strike = forward * 0.9  # ITM
            else:
                strike = forward * 1.1  # OTM
        else:
            strike = forward - d * vol * np.sqrt(time_to_maturity)
        
        return strike

    def _create_vol_point(self, strike, normal_vol, forward, delta, option_type, time_to_maturity):
        """
        Create a complete volatility point with all required fields.
        
        Args:
            strike: Strike price
            normal_vol: Normal volatility
            forward: Forward price
            delta: Delta value
            option_type: "call" or "put"
            time_to_maturity: Time to maturity in years
            
        Returns:
            Dict: Complete volatility point
        """
        # Calculate percentage volatility
        percentage_vol = (normal_vol / max(0.01, abs(forward))) * 100
        
        # Calculate relative strike (as percentage of forward)
        relative_strike = (strike / forward - 1) * 100 if forward != 0 else 0
        
        # Check if this is a key delta point
        is_key_delta = delta in [0.25, 0.5, 0.75]
        
        return {
            'strike': float(strike),
            'volatility': float(normal_vol),
            'percentage_vol': float(percentage_vol),
            'delta': float(delta),
            'relative_strike': float(relative_strike),
            'time_to_maturity': float(time_to_maturity),
            'is_key_delta': is_key_delta
        }
    
    def _get_historical_volatility(self, index: str, evaluation_date: datetime, days: int = 90) -> float:
        """
        Get historical volatility for an index from time series data
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

    def _get_historical_spread_volatility(self, index1: str, index2: str, evaluation_date: datetime, days: int = 90) -> float:
        """
        Get historical volatility for a spread between two indices
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

    def _calculate_correlation(self, index1: str, index2: str, evaluation_date: datetime, days: int = 90) -> float:
        """
        Calculate correlation between two indices
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

    def _generate_fallback_volatility_surface(self, indices: List[str], base_prices: Dict[str, float]) -> Dict[str, List[Dict[str, float]]]:
        """
        Generate a fallback volatility surface when the main method fails
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
                        spread_forward = base_prices.get(spread_name, base_prices.get(index1, 10.0) - base_prices.get(index2, 9.0))
                        spread_vol = max(0.3, (self.default_volatilities.get(index1, 0.35) + self.default_volatilities.get(index2, 0.35)) / 2)
                        
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
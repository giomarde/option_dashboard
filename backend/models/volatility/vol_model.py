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
        Calibrate Heston model parameters for stronger volatility smile.
        """
        print(f"DEBUG - calibrate_heston_parameters for {index}: base_vol={base_vol}, time={time_to_maturity}")
        
        # Convert from percentage (31%) to decimal (0.31) for Heston calculations
        decimal_vol = base_vol / 100.0
        print(f"DEBUG - Converting from percentage vol {base_vol}% to decimal {decimal_vol}")
        
        # Initial variance (v0) is square of volatility decimal
        v0 = decimal_vol**2
        print(f"DEBUG - v0 (initial variance): {v0}")
        
        # CRITICAL SMILE ENHANCEMENT
        
        # 1. Kappa (mean reversion speed)
        # - Force kappa to be small enough to create stronger smile
        # - Recommended range for visible smile: 0.1-0.8
        # - Ignore time_to_maturity formula that creates too high values
        kappa = 0.5  # Fixed value that works well for commodity smiles
        print(f"DEBUG - Fixed kappa (mean reversion): {kappa}")
        
        # 2. Theta (long-run variance)
        # - Keep theta = v0 for short maturities
        theta = v0
        print(f"DEBUG - theta (long-run variance): {theta}")
        
        # 3. Sigma (volatility of volatility)
        # - Critical for smile curvature
        # - Need sigma large enough relative to kappa
        # - sigma/kappa ratio determines curvature magnitude
        # - Target ratio of 1.0-2.0 for pronounced smile
        
        # Calculate sigma to achieve desired sigma/kappa ratio
        sigma_kappa_ratio = 1.5  # Target ratio for strong curvature
        sigma = kappa * sigma_kappa_ratio  # Ensure sigma is proportionally large enough
        print(f"DEBUG - sigma (vol-of-vol) set for ratio {sigma_kappa_ratio}: {sigma}")
        
        # 4. Rho (correlation)
        # - Controls smile asymmetry (skew)
        # - More negative = steeper downward slope on right side
        # - For commodity markets: usually -0.3 to -0.8
        
        # Different rho for different product types
        if "spread" in index.lower() or "-" in index:
            # Spread options typically have more pronounced skew
            rho = -0.7
        else:
            # Outright options
            rho = -0.6
        
        print(f"DEBUG - Fixed rho (correlation): {rho}")
        
        # Build parameters dict
        result = {
            'v0': v0,
            'kappa': kappa,
            'theta': theta,
            'sigma': sigma,
            'rho': rho
        }
        
        print(f"DEBUG - Final calibrated Heston params for {index}: {result}")
        
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
        Generate complete volatility surface data with proper debugging.
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
                
                # Generate points with higher density near ATM
                price_points = self._generate_price_points(forward_value, min_price, max_price, 100)
                
                # Step 4: Calculate Heston parameters based on historical vol
                heston_params = self.calibrate_heston_parameters(index, historical_vol, time_to_maturity)
                
                # Step 5: Generate volatility smile data points with detailed logging
                smile_data = []
                for price in price_points:
                    # Calculate moneyness (K/F)
                    moneyness = price / forward_value
                    
                    # Calculate Heston implied vol (as percentage)
                    percentage_vol_decimal = self.heston_implied_vol(moneyness, time_to_maturity, heston_params, option_type)
                    
                    # Convert to normal vol
                    normal_vol = percentage_vol_decimal * forward_value
                    
                    # Calculate delta at this point
                    delta = self._calculate_bachelier_delta(forward_value, price, time_to_maturity, normal_vol, option_type)
                    
                    # Log detailed information for key price points
                    if abs(price - forward_value) < 0.01 or price == min_price or price == max_price:
                        logger.info(f"Key price point for {index}: price={price:.4f}, moneyness={moneyness:.4f}, "
                                    f"percentage_vol={percentage_vol_decimal:.4f}, normal_vol={normal_vol:.4f}")
                    
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
                
                # Log a summary of the volatility range
                if smile_data:
                    min_vol = min(p['volatility'] for p in smile_data)
                    max_vol = max(p['volatility'] for p in smile_data)
                    atm_vol = next((p['volatility'] for p in smile_data if abs(p['strike'] - forward_value) < 0.01), None)
                    logger.info(f"Volatility range for {index}: min={min_vol:.4f}, max={max_vol:.4f}, atm={atm_vol:.4f}")
                
                # Store in result
                result[index] = smile_data
            
            # Process spreads with additional debugging and improvements
            if len(indices) > 1:
                for i, index1 in enumerate(indices):
                    for j, index2 in enumerate(indices):
                        if i < j:  # Avoid duplicate pairs
                            spread_name = f"{index1}-{index2}"
                            
                            # Get historical data for spread
                            spread_vol = self._get_historical_spread_volatility(index1, index2, evaluation_date)
                            logger.info(f"Historical volatility for {spread_name}: {spread_vol:.4f}")
                            
                            # Get forward value for spread
                            spread_forward = base_prices.get(spread_name, 
                                                            base_prices.get(index1, 10.0) - 
                                                            base_prices.get(index2, 9.0))
                            logger.info(f"Forward spread value for {spread_name}: {spread_forward:.4f}")
                            
                            # CRITICAL FIX: Special handling for near-zero spreads
                            # For spread options, we work in normal volatility space rather than percentage
                            # This avoids the division by near-zero spreads
                            
                            # Step 1: Calibrate parameters using normal volatility directly
                            # For spread options, we use the absolute volatility in parameter calibration
                            absolute_vol = spread_vol  # Keep as percentage for parameter calibration
                            heston_params = self.calibrate_spread_parameters(spread_name, absolute_vol, time_to_maturity)
                            
                            # Step 2: Generate spread range with appropriate points
                            # Ensure adequate coverage around ATM and zero
                            min_spread = min(-0.5, spread_forward - max(0.5, abs(spread_forward)))
                            max_spread = max(0.5, spread_forward + max(0.5, abs(spread_forward)))
                            
                            # Generate points with higher density near ATM and near 0
                            spread_points = self._generate_spread_points(spread_forward, min_spread, max_spread, 100)
                            
                            # Step 3: Generate smile data points for spread
                            spread_smile = []
                            for spread in spread_points:
                                # CRITICAL FIX: Handle moneyness calculation for near-zero spreads
                                # Traditional moneyness (K/F) breaks down when F approaches zero
                                
                                if abs(spread_forward) < 0.01:
                                    # For near-zero forward spreads, use absolute distance
                                    # normalized by a reference value (0.1 is a reasonable scale)
                                    moneyness = 1.0 + (spread - spread_forward) / 0.1
                                else:
                                    # For non-zero spreads, use standard moneyness
                                    moneyness = spread / spread_forward
                                
                                # Log specific issues with moneyness calculation
                                if not np.isfinite(moneyness) or moneyness <= 0:
                                    logger.warning(f"Invalid moneyness calculated: {moneyness} (spread={spread}, forward={spread_forward})")
                                    moneyness = 1.0  # Use safe default
                                
                                # CRITICAL FIX: Use modified approach for volatility calculation
                                if abs(spread_forward) < 0.01:
                                    # For near-zero spreads, work directly with normal volatility
                                    # Use a base normal vol and adjust based on distance from ATM
                                    base_normal_vol = spread_vol / 100.0  # Convert from percentage to decimal
                                    
                                    # Calculate normal vol directly with adjustment for distance from ATM
                                    # Higher vol for strikes further from ATM (quadratic shape)
                                    distance_from_atm = abs(spread - spread_forward)
                                    atm_adj_factor = 1.0 + (distance_from_atm * distance_from_atm * 2.0)
                                    normal_vol = base_normal_vol * atm_adj_factor
                                    
                                    # Calculate implied percentage vol (for display purposes only)
                                    # Use a reference value to avoid division by zero or tiny numbers
                                    reference_value = max(0.1, abs(spread_forward))
                                    percentage_vol = normal_vol / reference_value
                                else:
                                    # For regular spreads, use the Heston model
                                    percentage_vol = self.heston_implied_vol(moneyness, time_to_maturity, heston_params, option_type)
                                    
                                    # Convert to normal vol
                                    normal_vol = percentage_vol * abs(spread_forward)
                                
                                # Calculate delta (use standard Bachelier formula)
                                delta = self._calculate_bachelier_delta(spread_forward, spread, time_to_maturity, normal_vol, option_type)
                                
                                # Log key points for debugging
                                if abs(spread - spread_forward) < 0.01 or abs(spread) < 0.01 or spread == min_spread or spread == max_spread:
                                    logger.info(f"Key spread point: spread={spread:.4f}, moneyness={moneyness:.4f}, " 
                                            f"percentage_vol={percentage_vol*100:.4f}, normal_vol={normal_vol:.4f}")
                                
                                # Add data point to smile
                                spread_smile.append({
                                    'strike': float(spread),
                                    'volatility': float(normal_vol),
                                    'percentage_vol': float(percentage_vol * 100),  # Convert to percentage
                                    'delta': float(delta),
                                    'relative_strike': float(((spread - spread_forward) / max(0.1, abs(spread_forward))) * 100),
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
        Enhanced implementation for stronger smile shape.
        """
        
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
        
        # IMPROVED VOLATILITY FORMULA
        
        # Base ATM volatility
        atm_vol = np.sqrt(v0)
        
        # Calculate skew term - controls linear slope of smile
        # The formula is adjusted to create more pronounced effect
        skew_term = rho * sigma / kappa
        
        # Calculate curvature term - controls quadratic shape of smile
        # Using a simplified formula that creates stronger curvature
        curvature_term = (1 - rho**2) * sigma**2 / (2 * kappa**2)
    
        
        # Apply the improved approximation formula
        raw_implied_vol = atm_vol * (1 + skew_term * log_moneyness + curvature_term * log_moneyness**2)

        
        # Apply reasonable bounds but allow wide enough range for smile
        implied_vol = max(0.01, min(raw_implied_vol, 2.0))
        
        # Debug if bounds were applied

        
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

    def calibrate_spread_parameters(self, index, base_vol, time_to_maturity):
        """
        Special calibration method for spread options that handles volatility properly.
        """
        print(f"DEBUG - calibrate_spread_parameters for {index}: base_vol={base_vol}, time={time_to_maturity}")
        
        # For spread options, base_vol is already in percentage terms
        # Convert from percentage to decimal for parameter calculation
        decimal_vol = base_vol / 100.0
        print(f"DEBUG - Using percentage vol {base_vol}% as decimal {decimal_vol}")
        
        # Initial variance (v0) is square of volatility decimal
        v0 = decimal_vol**2
        print(f"DEBUG - v0 (initial variance): {v0}")
        
        # Use moderate kappa for spread options
        kappa = 0.5
        print(f"DEBUG - Spread kappa (mean reversion): {kappa}")
        
        # Long-run variance
        theta = v0
        print(f"DEBUG - theta (long-run variance): {theta}")
        
        # Volatility of volatility - important for smile shape
        # Use proportional approach
        sigma = 0.5  # Moderate value for stable results
        print(f"DEBUG - sigma (vol-of-vol): {sigma}")
        
        # Correlation parameter - controls asymmetry
        # Use moderate negative value for realistic downward skew
        rho = -0.3
        print(f"DEBUG - rho (correlation): {rho}")
        
        # Build parameters dict
        result = {
            'v0': v0,
            'kappa': kappa,
            'theta': theta,
            'sigma': sigma,
            'rho': rho
        }
        
        print(f"DEBUG - Final calibrated spread params: {result}")
        
        return result
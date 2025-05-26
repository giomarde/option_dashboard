# backend/models/volatility/vol_model.py

from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Union, Tuple
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VolatilityModel:
    """
    General volatility model that can calculate volatilities for 
    any indices and their spreads, suitable for all option types.
    """
    
    def __init__(self, data_provider=None):
        """
        Initialize the volatility model.
        
        Args:
            data_provider: Optional data provider instance
        """
        self.data_provider = data_provider
        self.historical_data_cache = {}  # Cache for historical data
        
        # Create an instance of the SpreadVolatilityModel for calculating spread volatilities
        self.spread_vol_model = SpreadVolatilityModel()
        
        # Default volatilities to use when historical data is not available
        self.default_volatilities = {
            'THE': 0.35,
            'TFU': 0.32,
            'JKM': 0.40,
            'DES': 0.38,
            'NBP': 0.33,
            'HH': 0.45,
        }
    
    def calculate_volatility(self, indices: List[str], 
                            evaluation_date: Union[str, datetime],
                            delivery_date: Union[str, datetime],
                            historical_length: int = 365) -> Dict[str, Union[float, Dict]]:
        """
        Calculate volatilities for multiple indices and their spreads.
        
        Args:
            indices: List of index names
            evaluation_date: Evaluation date
            delivery_date: Delivery date
            historical_length: Days of historical data to use
                
        Returns:
            Dict containing volatilities for all indices and their spreads
        """
        # Convert dates if needed
        if isinstance(evaluation_date, str):
            evaluation_date = datetime.strptime(evaluation_date, '%Y-%m-%d')
        if isinstance(delivery_date, str):
            delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d')
        
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
                    
                    # Fetch historical data - only load data, no vol calculation
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
        
        # Calculate individual volatilities using SpreadVolatilityModel
        individual_vols = {}
        for index in indices:
            # Use SpreadVolatilityModel for individual vol calculation
            vol = self.spread_vol_model.get_volatility_from_historical_data(
                historical_data[index], 
                pd.Series(),  # Empty series for second asset (not needed for single index)
                delivery_date
            )
            individual_vols[index] = vol
        
        # Calculate spread volatilities for all pairs and their smiles
        spread_vols = {}
        volatility_smiles = {}
        
        if len(indices) > 1:
            for i, index1 in enumerate(indices):
                # Add individual smile
                try:
                    price1 = historical_data[index1].iloc[-1] if len(historical_data[index1]) > 0 else 10.0
                    volatility_smiles[index1] = self.generate_volatility_smile(
                        individual_vols[index1], price1
                    )
                except Exception as e:
                    logger.error(f"Error generating smile for {index1}: {e}")
                
                for j, index2 in enumerate(indices):
                    if i < j:  # Avoid duplicate pairs and self-pairs
                        spread_name = f"{index1}-{index2}"
                        
                        # Use SpreadVolatilityModel for spread vol calculation
                        try:
                            vol = self.spread_vol_model.get_volatility_from_historical_data(
                                historical_data[index1],
                                historical_data[index2],
                                delivery_date
                            )
                            spread_vols[spread_name] = vol
                            
                            # Calculate the current spread value
                            price1 = historical_data[index1].iloc[-1] if len(historical_data[index1]) > 0 else 10.0
                            price2 = historical_data[index2].iloc[-1] if len(historical_data[index2]) > 0 else 9.0
                            spread_price = price1 - price2
                            
                            # Generate volatility smile for the spread
                            volatility_smiles[spread_name] = self.generate_volatility_smile(
                                vol, spread_price
                            )
                        except Exception as e:
                            logger.error(f"Error calculating spread vol for {spread_name}: {e}")
                            spread_vols[spread_name] = 0.35  # Default fallback
                            
                            # Generate default smile
                            price1 = historical_data[index1].iloc[-1] if len(historical_data[index1]) > 0 else 10.0
                            price2 = historical_data[index2].iloc[-1] if len(historical_data[index2]) > 0 else 9.0
                            spread_price = price1 - price2
                            volatility_smiles[spread_name] = self.generate_volatility_smile(
                                0.35, spread_price
                            )
        else:
            # Just one index, add its smile
            index = indices[0]
            try:
                price = historical_data[index].iloc[-1] if len(historical_data[index]) > 0 else 10.0
                volatility_smiles[index] = self.generate_volatility_smile(
                    individual_vols[index], price
                )
            except Exception as e:
                logger.error(f"Error generating smile for {index}: {e}")
        
        return {
            'individual': individual_vols,
            'spreads': spread_vols,
            'smiles': volatility_smiles
        }
    
    def generate_volatility_smile(self, base_vol: float, 
                                base_price: float,
                                strikes: Optional[List[float]] = None,
                                option_strike: Optional[float] = None) -> List[Dict[str, float]]:
        """
        Generate a volatility smile around a base volatility.
        
        Args:
            base_vol: Base ATM volatility
            base_price: Current price or spread value
            strikes: Optional list of strike prices
            option_strike: The actual option strike price (if available)
            
        Returns:
            List of dictionaries with strike and volatility pairs
        """
        # Safety check for base_price
        if base_price == 0:
            logger.warning("Base price is zero, using default value of 1.0")
            base_price = 1.0
        
        # Round for cleaner calculations
        base_price = round(base_price, 4)
        base_vol = round(base_vol, 4)
        
        # If we have an option strike, use that as the center for our smile
        center_price = option_strike if option_strike is not None else base_price
        
        if strikes is None:
            # Generate more strikes over a wider range
            # Use 2x the difference between center and base price to ensure wide enough range
            range_width = max(0.3 * abs(center_price), abs(center_price - base_price) * 2, 0.3)
            
            # Create 9 points for a smoother smile
            num_strikes = 9
            
            # Generate strikes around the center price
            strikes = [round(center_price + (i - (num_strikes - 1) / 2) * range_width / (num_strikes - 1), 4) 
                    for i in range(num_strikes)]
            
            # Make sure we have a point at exactly the center price and the base price
            if center_price not in strikes:
                strikes.append(round(center_price, 4))
            if base_price not in strikes and center_price != base_price:
                strikes.append(round(base_price, 4))
            
            # Sort and remove duplicates
            strikes = sorted(list(set(strikes)))
                
            # Log the strikes to verify ATM centering
            logger.debug(f"Generated strikes around {center_price} (current spread: {base_price}): {strikes}")
        
        # Generate volatility smile
        smile = []
        for strike in strikes:
            # Calculate moneyness (how far from ATM)
            moneyness = strike / center_price - 1 if center_price != 0 else 0
            
            # Apply smile effect - more pronounced for extreme strikes
            smile_factor = 1 + 0.7 * moneyness**2  # Increased for more pronounced smile
            
            # Skew effect - typically higher volatilities for lower strikes (put skew)
            skew_factor = 1 - 0.2 * moneyness  # Increased for more skew
            
            # Combine effects
            vol = base_vol * smile_factor * skew_factor
            
            # Ensure vol is reasonable and round to 4 decimal places
            vol = round(min(max(0.1, vol), 0.8), 4)
            
            smile.append({
                'strike': strike,
                'volatility': vol,
                'relative_strike': round(100 * (strike / center_price - 1), 2) if center_price != 0 else 0  # Add relative strike as percentage
            })
        
        # Sort by strike for proper display
        smile.sort(key=lambda x: x['strike'])
        
        # Log the smile
        logger.debug(f"Generated volatility smile for center price {center_price}: {smile}")
        
        return smile
    
    def get_volatility_surface(self, indices: List[str],
                                evaluation_date: Union[str, datetime],
                                delivery_date: Union[str, datetime],
                                base_prices: Optional[Dict[str, float]] = None,
                                option_strikes: Optional[Dict[str, float]] = None) -> Dict[str, List[Dict[str, float]]]:
        """
        Generate complete volatility surface data for indices and spreads.
        
        Args:
            indices: List of indices to generate volatility surface for
            evaluation_date: The evaluation date
            delivery_date: The delivery date
            base_prices: Dictionary of base prices for each index/spread
            option_strikes: Dictionary of option strikes for each index/spread
        
        Returns:
            Dictionary of volatility smiles for each index/spread
        """
        try:
            # Calculate base volatilities
            vols = self.calculate_volatility(indices, evaluation_date, delivery_date)
            
            # If base prices not provided, create dummy values
            if base_prices is None:
                base_prices = {index: 10.0 for index in indices}
                
            # If option strikes not provided, initialize empty dict
            if option_strikes is None:
                option_strikes = {}
                    
            # Add spread prices if not provided
            if len(indices) > 1:
                for i, index1 in enumerate(indices):
                    for j, index2 in enumerate(indices):
                        if i < j:  # Avoid duplicate pairs and self-pairs
                            spread_name = f"{index1}-{index2}"
                            if spread_name not in base_prices and index1 in base_prices and index2 in base_prices:
                                base_prices[spread_name] = round(base_prices[index1] - base_prices[index2], 4)
            
            # Generate volatility smiles
            result = {}
            
            # Individual indices
            for index, vol in vols['individual'].items():
                if index in base_prices:
                    # Calculate appropriate strikes around the current price
                    current_price = base_prices[index]
                    option_strike = option_strikes.get(index)
                    result[index] = self.generate_volatility_smile(vol, current_price, option_strike=option_strike)
            
            # Spreads
            for spread_name, vol in vols['spreads'].items():
                if spread_name in base_prices:
                    # Get the option strike for this spread if available
                    option_strike = option_strikes.get(spread_name)
                    current_spread = base_prices[spread_name]
                    
                    # Generate volatility smile around both the current spread and the option strike
                    result[spread_name] = self.generate_volatility_smile(vol, current_spread, option_strike=option_strike)
            
            return result
        except Exception as e:
            logger.error(f"Error in get_volatility_surface: {e}")
            # Create a minimal set of fallback volatility smiles
            fallback = {}
            for index in indices:
                fallback[index] = [
                    {"strike": 10.0 * 0.9, "volatility": 0.33, "relative_strike": -10.0},
                    {"strike": 10.0, "volatility": 0.30, "relative_strike": 0.0},
                    {"strike": 10.0 * 1.1, "volatility": 0.33, "relative_strike": 10.0}
                ]
            
            # Add a spread smile if needed
            if len(indices) > 1:
                spread_name = f"{indices[0]}-{indices[1]}"
                fallback[spread_name] = [
                    {"strike": 1.0 * 0.5, "volatility": 0.36, "relative_strike": -50.0},
                    {"strike": 1.0, "volatility": 0.35, "relative_strike": 0.0},
                    {"strike": 1.0 * 1.5, "volatility": 0.36, "relative_strike": 50.0}
                ]
            
            return fallback


class SpreadVolatilityModel:
    """
    Optimized class for modeling and forecasting spread volatility 
    that reuses already fetched data
    """
    
    def __init__(self):
        self.model = None
        self.model_results = None
        self.model_params = None
        self.historical_data_cache = {}  # Cache for historical data
        self.heston_params = {
            "v0": 0.04,     # Initial variance
            "kappa": 1.5,   # Mean reversion speed
            "theta": 0.04,  # Long-run variance
            "sigma": 0.3,   # Vol of vol
            "rho": -0.7     # Correlation
        }
        
    def get_volatility_from_historical_data(self, asset1_prices, asset2_prices, 
                                        delivery_date, historical_length=365):
        """
        Calculate volatility from provided historical data with improved modeling
        
        Args:
            asset1_prices (pd.Series): Historical prices for asset1
            asset2_prices (pd.Series): Historical prices for asset2
            delivery_date (datetime): Delivery date
            historical_length (int): Days of historical data to use
                
        Returns:
            float: Estimated volatility for the spread
        """
        try:
            # Handle single asset case
            if asset2_prices is None or len(asset2_prices) == 0:
                return self.estimate_volatility_from_spread_series(asset1_prices)
            
            # Debug: Check input data shapes and types
            logger.debug(f"asset1_prices type: {type(asset1_prices)}, len: {len(asset1_prices)}")
            logger.debug(f"asset2_prices type: {type(asset2_prices)}, len: {len(asset2_prices)}")
            
            # Ensure both are pandas Series with datetime index
            if not isinstance(asset1_prices, pd.Series):
                logger.warning("asset1_prices is not a pandas Series, converting...")
                asset1_prices = pd.Series(asset1_prices)
                
            if not isinstance(asset2_prices, pd.Series):
                logger.warning("asset2_prices is not a pandas Series, converting...")
                asset2_prices = pd.Series(asset2_prices)
            
            # Align the two series on the same dates
            combined = pd.DataFrame({
                'asset1': asset1_prices,
                'asset2': asset2_prices
            })
            
            # IMPORTANT FIX: Ensure the data is sorted by date index in descending order
            # This ensures that 'most recent' actually means most recent chronologically
            combined = combined.sort_index(ascending=False)
            
            # Debug: Print first few rows to verify data alignment and sorting
            logger.debug(f"First 5 rows of combined data (after sorting):")
            logger.debug(combined.head(5))
            
            # Drop any rows with missing values
            combined_clean = combined.dropna()
            logger.debug(f"After dropping NAs: {len(combined_clean)} rows")
            
            # Use last N days of data - now properly sorted by date
            if len(combined_clean) > historical_length:
                combined_clean = combined_clean.head(historical_length)  # Using head() now since index is descending
                logger.debug(f"After limiting to most recent {historical_length} days: {len(combined_clean)} rows")
            
            # Check if we have enough data
            if len(combined_clean) < 20:
                logger.warning(f"Limited historical data ({len(combined_clean)} points). Using default volatility.")
                return 0.3  # Default fallback for limited data
            
            # Calculate the spread between assets
            spread_series = combined_clean['asset1'] - combined_clean['asset2']
            
            # Debug: Print spread statistics with date range
            first_date = combined_clean.index.min().strftime('%Y-%m-%d')
            last_date = combined_clean.index.max().strftime('%Y-%m-%d')
            logger.debug(f"Spread series statistics ({first_date} to {last_date}):")
            logger.debug(f"Mean: {spread_series.mean()}, Min: {spread_series.min()}, Max: {spread_series.max()}")
            logger.debug(f"First 5 spread values (most recent first): {spread_series.head(5).tolist()}")
            
            # Get historical spread volatility with 20-day and 60-day windows
            # Using the most recent data now due to proper sorting
            vol_20d = self.estimate_volatility_from_spread_series(spread_series.head(min(20, len(spread_series))))
            vol_60d = self.estimate_volatility_from_spread_series(spread_series.head(min(60, len(spread_series))))
            
            # Debug: Print raw volatility calculations
            logger.debug(f"Raw vol_20d: {vol_20d}, Raw vol_60d: {vol_60d}")
            
            # Blend volatilities (more weight to recent data)
            base_vol = 0.5 * vol_20d + 0.5 * vol_60d
            
            # Apply seasonal adjustment based on delivery month
            delivery_month = delivery_date.month
            seasonal_factor = 1.0
            
            # Typically winter months (Dec-Feb) have higher volatility
            if delivery_month in [12, 1, 2]:
                seasonal_factor = 1.2
            # Shoulder months (Mar-Apr, Oct-Nov) have moderate volatility  
            elif delivery_month in [3, 4, 10, 11]:
                seasonal_factor = 1.1
            # Summer months (May-Sep) have lower volatility
            else:
                seasonal_factor = 0.9
            
            # Calculate days to delivery and apply term structure adjustment
            days_to_delivery = (delivery_date - datetime.now()).days
            
            if days_to_delivery > 0:
                time_to_maturity = days_to_delivery / 365
                vol = self.calculate_term_structure(base_vol, [time_to_maturity])[0]
                
                # Apply a reasonableness cap (don't let vol exceed 0.8 in absolute terms)
                vol = min(vol, 0.8)
            else:
                vol = min(base_vol, 0.8)
            
            use_heston = True
            if use_heston and days_to_delivery > 0:
                spread_start = spread_series.iloc[0]
                time_to_maturity = max(days_to_delivery / 365, 1 / 252)  # Avoid division by 0

                # Show vols at surrounding levels to visualize the smile
                logger.debug("Heston implied vol smile:")
                for pct in [-0.1, -0.05, 0.0, 0.05, 0.1]:
                    S_test = spread_start * (1 + pct)
                    vol_test = self.simulate_heston_volatility(S0=S_test, T=time_to_maturity)
                    logger.debug(f"  Spread: {S_test:.4f} ({pct:+.0%}), Implied Vol: {vol_test:.4f}")

                # Use the base spread for final vol
                heston_vol = self.simulate_heston_volatility(S0=spread_start, T=time_to_maturity)
                logger.debug(f"Heston implied vol at current spread ({spread_start:.4f}): {heston_vol:.4f}")
                vol = min(heston_vol, 0.8)

            # Diagnostic prints
            logger.info(f"Volatility calculation for delivery {delivery_date.strftime('%b-%Y')}:")
            logger.info(f"  20-day vol: {vol_20d:.4f}")
            logger.info(f"  60-day vol: {vol_60d:.4f}")
            logger.info(f"  Base vol: {base_vol:.4f}")
            logger.info(f"  Seasonal factor: {seasonal_factor:.2f}")
            logger.info(f"  Days to delivery: {days_to_delivery}")
            logger.info(f"  Final vol: {vol:.4f}")

            return vol
            
        except Exception as e:
            logger.error(f"Error calculating volatility from historical data: {e}")
            import traceback
            traceback.print_exc()
            return 0.3  # Default fallback
    
    def estimate_volatility_from_spread_series(self, spread_series, annualize=True):
        """
        Calculate volatility directly from spread time series
        
        Args:
            spread_series (pd.Series): Time series of spread values
            annualize (bool): Whether to annualize the volatility
            
        Returns:
            float: Estimated volatility
        """
        # Debug: Print input
        logger.debug(f"estimate_volatility input: {len(spread_series)} points")
        
        # IMPORTANT FIX: Ensure data is sorted chronologically for proper differencing
        # For proper price changes, we need to calculate day-to-day changes
        # This requires chronological ordering (ascending by date)
        spread_series_chrono = spread_series.sort_index()
        
        # For Bachelier model, use absolute changes
        spread_changes = spread_series_chrono.diff().dropna()
        
        # Debug: Print changes
        logger.debug(f"First 5 spread changes: {spread_changes.head(5).tolist()}")
        logger.debug(f"Spread changes stats: Mean={spread_changes.mean()}, Std={spread_changes.std()}")
        
        # Calculate volatility (standard deviation of changes)
        vol = spread_changes.std()
        
        # Annualize if requested (assuming 252 trading days)
        if annualize:
            vol = vol * np.sqrt(252)
        
        # IMPORTANT FIX: Return the volatility as a decimal, not a percentage
        vol = vol / 100.0  # Convert from percentage to decimal
        
        logger.debug(f"Calculated volatility: {vol}")
        
        return vol
    
    def calculate_term_structure(self, base_vol, maturities, mean_reversion=0.5):
        """
        Calculate the term structure of volatility
        
        Args:
            base_vol (float): Base volatility (annualized)
            maturities (list): List of maturities in years
            mean_reversion (float): Mean reversion rate
            
        Returns:
            np.array: Term structure of volatilities
        """
        vol_term = []
        
        for T in maturities:
            if T <= 0:
                vol_term.append(base_vol)
            else:
                # Calculate term structure with mean reversion
                term_factor = np.sqrt((1 - np.exp(-2 * mean_reversion * T)) / (2 * mean_reversion * T))
                vol_term.append(base_vol * term_factor)
        
        return np.array(vol_term)
    
    def simulate_heston_volatility(self, S0, T, steps=252, n_paths=1000):
        """
        Simulates Heston model paths and returns the implied volatility
        
        Args:
            S0 (float): Initial spread value
            T (float): Time to maturity in years
            steps (int): Time steps per year
            n_paths (int): Number of Monte Carlo paths
        
        Returns:
            float: Implied volatility (standard deviation of log returns)
        """
        dt = T / steps
        v0 = self.heston_params["v0"]
        kappa = self.heston_params["kappa"]
        theta = self.heston_params["theta"]
        sigma = self.heston_params["sigma"]
        rho = self.heston_params["rho"]
        
        v = np.full((n_paths,), v0)
        S = np.full((n_paths,), S0)

        for _ in range(steps):
            z1 = np.random.normal(size=n_paths)
            z2 = np.random.normal(size=n_paths)
            dw1 = z1
            dw2 = rho * z1 + np.sqrt(1 - rho**2) * z2

            v = np.abs(v + kappa * (theta - v) * dt + sigma * np.sqrt(v * dt) * dw2)
            S = S * np.exp(-0.5 * v * dt + np.sqrt(v * dt) * dw1)
        
        log_returns = np.log(S / S0)
        implied_vol = np.std(log_returns) / np.sqrt(T)
        
        return implied_vol
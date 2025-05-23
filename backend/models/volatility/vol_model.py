"""
Volatility model implementation with improved error handling.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Union, Tuple

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
        self.heston_params = {
            "v0": 0.04,     # Initial variance
            "kappa": 1.5,   # Mean reversion speed
            "theta": 0.04,  # Long-run variance
            "sigma": 0.3,   # Vol of vol
            "rho": -0.7     # Correlation
        }
        
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
        
        # Calculate individual volatilities
        individual_vols = {}
        for index in indices:
            individual_vols[index] = self.estimate_volatility(
                historical_data[index], delivery_date, index=index)
        
        # Calculate spread volatilities for all pairs
        spread_vols = {}
        if len(indices) > 1:
            for i, index1 in enumerate(indices):
                for j, index2 in enumerate(indices):
                    if i < j:  # Avoid duplicate pairs and self-pairs
                        spread_name = f"{index1}-{index2}"
                        spread_vols[spread_name] = self.estimate_spread_volatility(
                            historical_data[index1], 
                            historical_data[index2],
                            delivery_date,
                            index1=index1,
                            index2=index2
                        )
        
        return {
            'individual': individual_vols,
            'spreads': spread_vols
        }
    
    def estimate_volatility(self, price_series: pd.Series, 
                           delivery_date: datetime,
                           annualize: bool = True,
                           index: str = None) -> float:
        """
        Estimate volatility for a single index.
        
        Args:
            price_series: Historical price series
            delivery_date: Delivery date
            annualize: Whether to annualize the volatility
            index: The index name (for fallback defaults)
            
        Returns:
            Estimated volatility
        """
        # Check if we have enough data
        if price_series is None or len(price_series) < 2:
            logger.warning(f"Insufficient data for volatility calculation for {index}, using default")
            # Use default volatility if index is provided, otherwise use a general default
            if index and index in self.default_volatilities:
                return self.default_volatilities[index]
            return 0.3  # Default volatility
        
        try:
            # Make sure the series is sorted
            price_series = price_series.sort_index()
            
            # Calculate log returns (for Black-Scholes) or price changes (for Bachelier)
            # Here we're using log returns as a general approach
            # First check if there are any non-positive values
            if (price_series <= 0).any():
                # Use price changes instead of log returns for Bachelier model
                returns = price_series.diff().dropna()
                
                # Use absolute values for volatility calculation
                if returns.abs().mean() > 0:
                    vol = returns.std() / returns.abs().mean()
                else:
                    # Fallback if mean is zero
                    vol = returns.std()
                    if vol == 0:
                        logger.warning(f"Zero standard deviation for {index}, using default")
                        if index and index in self.default_volatilities:
                            return self.default_volatilities[index]
                        return 0.3
            else:
                # Use log returns for Black-Scholes style calculation
                returns = np.log(price_series / price_series.shift(1)).dropna()
                
                # Calculate volatility
                vol = returns.std()
                
                # If volatility is zero or nan, use default
                if vol == 0 or np.isnan(vol):
                    logger.warning(f"Zero or NaN volatility for {index}, using default")
                    if index and index in self.default_volatilities:
                        return self.default_volatilities[index]
                    return 0.3
            
            # Annualize if requested (assuming 252 trading days)
            if annualize:
                vol = vol * np.sqrt(252)
            
            # Apply seasonal adjustment
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
            
            vol = vol * seasonal_factor
            
            # Apply term structure adjustment
            days_to_delivery = (delivery_date - datetime.now()).days
            if days_to_delivery > 0:
                time_to_maturity = days_to_delivery / 365
                # Avoid division by zero
                if time_to_maturity > 0:
                    term_factor = np.sqrt((1 - np.exp(-2 * 0.5 * time_to_maturity)) / (2 * 0.5 * time_to_maturity))
                    vol = vol * term_factor
            
            # Cap the volatility to reasonable levels
            vol = min(max(0.1, vol), 0.8)
            
            return vol
        except Exception as e:
            logger.error(f"Error calculating volatility for {index}: {e}")
            # Use default volatility if index is provided, otherwise use a general default
            if index and index in self.default_volatilities:
                return self.default_volatilities[index]
            return 0.3  # Default fallback volatility
    
    def estimate_spread_volatility(self, price_series1: pd.Series, 
                                  price_series2: pd.Series,
                                  delivery_date: datetime,
                                  correlation: Optional[float] = None,
                                  index1: str = None,
                                  index2: str = None) -> float:
        """
        Estimate volatility for a spread between two indices.
        
        Args:
            price_series1: Historical price series for first index
            price_series2: Historical price series for second index
            delivery_date: Delivery date
            correlation: Optional correlation override
            index1: The first index name (for fallback defaults)
            index2: The second index name (for fallback defaults)
            
        Returns:
            Estimated spread volatility
        """
        # Get individual volatilities with fallback
        vol1 = self.estimate_volatility(price_series1, delivery_date, index=index1)
        vol2 = self.estimate_volatility(price_series2, delivery_date, index=index2)
        
        # Check if we have enough data for both series
        if price_series1 is None or price_series2 is None or len(price_series1) < 2 or len(price_series2) < 2:
            logger.warning(f"Insufficient data for spread volatility calculation between {index1} and {index2}, using individual vols")
            
            # If correlation is not provided, use a default value
            if correlation is None:
                correlation = 0.7  # Default high correlation for energy markets
            
            # Calculate spread volatility using individual volatilities and correlation
            spread_vol = np.sqrt(vol1**2 + vol2**2 - 2 * correlation * vol1 * vol2)
            
            # Cap the volatility to reasonable levels
            spread_vol = min(max(0.1, spread_vol), 0.8)
            
            return spread_vol
        
        try:
            # Make sure the series are sorted
            price_series1 = price_series1.sort_index()
            price_series2 = price_series2.sort_index()
            
            # Align the series
            combined = pd.DataFrame({
                'asset1': price_series1,
                'asset2': price_series2
            })
            combined = combined.dropna()
            
            if len(combined) < 2:
                logger.warning(f"Insufficient aligned data for spread volatility calculation between {index1} and {index2}, using individual vols")
                
                # If correlation is not provided, use a default value
                if correlation is None:
                    correlation = 0.7  # Default high correlation for energy markets
                
                # Calculate spread volatility using individual volatilities and correlation
                spread_vol = np.sqrt(vol1**2 + vol2**2 - 2 * correlation * vol1 * vol2)
                
                # Cap the volatility to reasonable levels
                spread_vol = min(max(0.1, spread_vol), 0.8)
                
                return spread_vol
            
            # Calculate the spread
            spread = combined['asset1'] - combined['asset2']
            
            # Method 1: Direct calculation from spread series
            vol_direct = self.estimate_volatility(spread, delivery_date)
            
            # Method 2: Calculate from individual volatilities and correlation
            # Check for non-positive values before taking log
            if (combined['asset1'] <= 0).any() or (combined['asset2'] <= 0).any():
                # Use price changes
                returns1 = combined['asset1'].diff().dropna()
                returns2 = combined['asset2'].diff().dropna()
                
                if len(returns1) > 0 and len(returns2) > 0:
                    # Normalize by mean absolute value to get something like volatility
                    if returns1.abs().mean() > 0:
                        vol1 = returns1.std() / returns1.abs().mean()
                    else:
                        vol1 = returns1.std()
                        
                    if returns2.abs().mean() > 0:
                        vol2 = returns2.std() / returns2.abs().mean()
                    else:
                        vol2 = returns2.std()
                    
                    # Annualize
                    vol1 = vol1 * np.sqrt(252)
                    vol2 = vol2 * np.sqrt(252)
                    
                    # Calculate correlation
                    if correlation is None:
                        # Check for constant series
                        if returns1.std() > 0 and returns2.std() > 0:
                            correlation = returns1.corr(returns2)
                        else:
                            correlation = 0.0
                else:
                    # Fallback to default correlation
                    correlation = 0.7
            else:
                # Use log returns
                returns1 = np.log(combined['asset1'] / combined['asset1'].shift(1)).dropna()
                returns2 = np.log(combined['asset2'] / combined['asset2'].shift(1)).dropna()
                
                vol1 = returns1.std() * np.sqrt(252)
                vol2 = returns2.std() * np.sqrt(252)
                
                if correlation is None:
                    correlation = returns1.corr(returns2)
            
            # Calculate volatility from individual components
            vol_from_components = np.sqrt(vol1**2 + vol2**2 - 2 * correlation * vol1 * vol2)
            
            # Blend the two methods
            spread_vol = 0.7 * vol_direct + 0.3 * vol_from_components
            
            # Apply seasonal adjustment
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
            
            spread_vol = spread_vol * seasonal_factor
            
            # Cap the volatility to reasonable levels
            spread_vol = min(max(0.1, spread_vol), 0.8)
            
            return spread_vol
        except Exception as e:
            logger.error(f"Error calculating spread volatility between {index1} and {index2}: {e}")
            
            # If correlation is not provided, use a default value
            if correlation is None:
                correlation = 0.7  # Default high correlation for energy markets
            
            # Calculate spread volatility using individual volatilities and correlation
            spread_vol = np.sqrt(vol1**2 + vol2**2 - 2 * correlation * vol1 * vol2)
            
            # Cap the volatility to reasonable levels
            spread_vol = min(max(0.1, spread_vol), 0.8)
            
            return spread_vol
    
    def generate_volatility_smile(self, base_vol: float, 
                                 base_price: float,
                                 strikes: Optional[List[float]] = None) -> List[Dict[str, float]]:
        """
        Generate a volatility smile around a base volatility.
        
        Args:
            base_vol: Base ATM volatility
            base_price: Current price or spread value
            strikes: Optional list of strike prices
            
        Returns:
            List of dictionaries with strike and volatility pairs
        """
        # Safety check for base_price
        if base_price == 0:
            logger.warning("Base price is zero, using default value of 1.0")
            base_price = 1.0
        
        if strikes is None:
            # Generate strikes around the base price
            range_pct = 0.2  # 20% range around base price
            num_strikes = 5
            strikes = [base_price * (1 + (i - (num_strikes - 1) / 2) * range_pct / (num_strikes - 1)) 
                      for i in range(num_strikes)]
        
        # Generate volatility smile
        smile = []
        for strike in strikes:
            # Calculate moneyness
            moneyness = strike / base_price - 1
            
            # Apply smile effect - more pronounced for extreme strikes
            smile_factor = 1 + 0.5 * moneyness**2
            
            # Skew effect - typically higher volatilities for lower strikes (put skew)
            skew_factor = 1 - 0.1 * moneyness
            
            # Combine effects
            vol = base_vol * smile_factor * skew_factor
            
            # Ensure vol is reasonable
            vol = min(max(0.1, vol), 0.8)
            
            smile.append({
                'strike': strike,
                'volatility': vol
            })
        
        return smile
    
    def get_volatility_surface(self, indices: List[str],
                              evaluation_date: Union[str, datetime],
                              delivery_date: Union[str, datetime],
                              base_prices: Optional[Dict[str, float]] = None) -> Dict[str, List[Dict[str, float]]]:
        """
        Generate complete volatility surface data for indices and spreads.
        
        Args:
            indices: List of index names
            evaluation_date: Evaluation date
            delivery_date: Delivery date
            base_prices: Dictionary of current prices for indices
            
        Returns:
            Dictionary with volatility smiles for all indices and spreads
        """
        # Calculate base volatilities
        vols = self.calculate_volatility(indices, evaluation_date, delivery_date)
        
        # If base prices not provided, create dummy values
        if base_prices is None:
            base_prices = {index: 10.0 for index in indices}
            
            # Add spread prices
            if len(indices) > 1:
                for i, index1 in enumerate(indices):
                    for j, index2 in enumerate(indices):
                        if i < j:  # Avoid duplicate pairs and self-pairs
                            spread_name = f"{index1}-{index2}"
                            base_prices[spread_name] = base_prices[index1] - base_prices[index2]
        
        # Generate volatility smiles
        result = {}
        
        # Safety check for base_prices
        for index, price in base_prices.items():
            if price == 0:
                logger.warning(f"Base price for {index} is zero, using default value of 1.0")
                base_prices[index] = 1.0
        
        # Individual indices
        for index, vol in vols['individual'].items():
            if index in base_prices:
                result[index] = self.generate_volatility_smile(vol, base_prices[index])
        
        # Spreads
        for spread_name, vol in vols['spreads'].items():
            if spread_name in base_prices:
                result[spread_name] = self.generate_volatility_smile(vol, base_prices[spread_name])
        
        return result
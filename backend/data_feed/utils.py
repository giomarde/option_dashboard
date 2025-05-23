"""
Utility functions for working with market data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
import logging

from . import get_data_provider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_forward_curves(primary_index: str, secondary_index: str, 
                      start_date: Optional[Union[str, datetime]] = None,
                      end_date: Optional[Union[str, datetime]] = None,
                      provider_type: str = 'csv') -> Dict:
    """
    Get forward curves for two indices
    
    Args:
        primary_index: The primary index
        secondary_index: The secondary index
        start_date: Start date for the forward curves
        end_date: End date for the forward curves
        provider_type: The type of data provider to use
        
    Returns:
        Dict: A dictionary with forward curve data for both indices
    """
    provider = get_data_provider(provider_type)
    
    if start_date is None:
        start_date = datetime.now().strftime('%Y-%m-%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Get forward curves for both indices
    primary_curve = provider.fetch_forward_curve(primary_index, curve_date=start_date)
    secondary_curve = provider.fetch_forward_curve(secondary_index, curve_date=start_date)
    
    # Calculate spreads
    spreads = []
    dates = []
    
    # Match months between the two curves
    for col in primary_curve.columns:
        if col in secondary_curve.columns:
            primary_price = primary_curve.iloc[0][col]
            secondary_price = secondary_curve.iloc[0][col]
            
            if pd.notna(primary_price) and pd.notna(secondary_price):
                spread = primary_price - secondary_price
                spreads.append(spread)
                
                # Get the date for this contract month
                month_num = int(col.replace('M', ''))
                contract_date = pd.to_datetime(start_date) + pd.DateOffset(months=month_num-1)
                dates.append(contract_date.strftime('%Y-%m-%d'))
    
    return {
        "primary_index": primary_index,
        "secondary_index": secondary_index,
        "primary_curve": primary_curve.to_dict('records')[0] if not primary_curve.empty else {},
        "secondary_curve": secondary_curve.to_dict('records')[0] if not secondary_curve.empty else {},
        "spreads": spreads,
        "dates": dates
    }

def get_market_data_for_indices(indices: List[str], 
                              date: Optional[Union[str, datetime]] = None,
                              provider_type: str = 'csv') -> Dict:
    """
    Get market data for multiple indices
    
    Args:
        indices: List of indices to fetch data for
        date: The date for which to fetch data
        provider_type: The type of data provider to use
        
    Returns:
        Dict: A dictionary with market data for all indices
    """
    provider = get_data_provider(provider_type)
    
    result = {}
    
    for index in indices:
        try:
            data = provider.fetch_market_data(index, date)
            result[index] = data
        except Exception as e:
            logger.error(f"Error fetching market data for {index}: {e}")
            result[index] = {
                "price": None,
                "lastUpdated": None,
                "error": str(e)
            }
    
    return result

def get_volatility_data(primary_index: str, secondary_index: Optional[str] = None,
                      date: Optional[Union[str, datetime]] = None,
                      provider_type: str = 'csv') -> Dict:
    """
    Get volatility data for indices
    
    Args:
        primary_index: The primary index
        secondary_index: Optional secondary index for spread volatilities
        date: The date for which to fetch data
        provider_type: The type of data provider to use
        
    Returns:
        Dict: A dictionary with volatility data
    """
    provider = get_data_provider(provider_type)
    
    try:
        return provider.fetch_volatility_surface(primary_index, secondary_index, date)
    except Exception as e:
        logger.error(f"Error fetching volatility data: {e}")
        return {
            "error": str(e)
        }
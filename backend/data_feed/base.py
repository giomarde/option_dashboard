"""
Base class for data feed providers
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Optional, Union
from datetime import datetime, date


class DataFeedProvider(ABC):
    """
    Abstract base class for all data feed providers
    
    This defines the interface that all data providers must implement,
    ensuring consistency across different data sources.
    """
    
    @abstractmethod
    def fetch_data(self, ticker: str, start_date: Union[str, date, datetime], 
                   end_date: Union[str, date, datetime], field: str = 'PX_LAST') -> pd.Series:
        """
        Fetch price data for a specific ticker
        
        Args:
            ticker: The ticker symbol
            start_date: Start date for the data range
            end_date: End date for the data range
            field: The field to fetch (e.g., 'PX_LAST' for last price)
            
        Returns:
            pd.Series: A pandas Series with dates as index and prices as values
        """
        pass
    
    @abstractmethod
    def fetch_forward_curve(self, base_ticker: str, num_months: int = 12,
                            curve_date: Optional[Union[str, date, datetime]] = None) -> pd.DataFrame:
        """
        Fetch forward curve for a base ticker
        
        Args:
            base_ticker: The base ticker symbol
            num_months: Number of months to fetch in the forward curve
            curve_date: The date for which to fetch the forward curve
            
        Returns:
            pd.DataFrame: A dataframe with forward curve data
        """
        pass
    
    @abstractmethod
    def fetch_market_data(self, ticker: str, date: Optional[Union[str, date, datetime]] = None) -> Dict:
        """
        Fetch latest market data for a ticker
        
        Args:
            ticker: The ticker symbol
            date: The date for which to fetch market data (None for latest)
            
        Returns:
            Dict: A dictionary with market data (price, volatility, etc.)
        """
        pass
    
    @abstractmethod
    def fetch_volatility_surface(self, primary_ticker: str, secondary_ticker: Optional[str] = None,
                                date: Optional[Union[str, date, datetime]] = None) -> Dict:
        """
        Fetch volatility surface data
        
        Args:
            primary_ticker: The primary ticker symbol
            secondary_ticker: Optional secondary ticker for spread volatilities
            date: The date for which to fetch volatility data
            
        Returns:
            Dict: A dictionary with volatility surface data
        """
        pass
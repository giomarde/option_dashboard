"""
Data Feed Module

This module provides interfaces for fetching market data from various sources.
"""

from .base import DataFeedProvider
from .csv_provider import CSVDataFeedProvider

# Factory function to get the appropriate data provider
def get_data_provider(provider_type='csv', **kwargs):
    """
    Get a data provider instance based on the specified type
    
    Args:
        provider_type: The type of data provider to use ('csv', 'api', etc.)
        **kwargs: Additional arguments to pass to the provider constructor
        
    Returns:
        DataFeedProvider: An instance of the appropriate data provider
    """
    if provider_type == 'csv':
        return CSVDataFeedProvider(**kwargs)
    elif provider_type == 'api':
        # Future implementation for API-based data feed
        raise NotImplementedError("API data provider not yet implemented")
    else:
        raise ValueError(f"Unknown data provider type: {provider_type}")
"""
Base class for pricing models.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePricingModel(ABC):
    """
    Abstract base class for all pricing models.
    All pricing models should inherit from this class and implement the required methods.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the pricing model with configuration parameters.
        
        Args:
            config: Dictionary containing configuration parameters for the model
        """
        self.config = config
        self.results = {}
        
    @abstractmethod
    def prepare_input_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare the input data required for the pricing model.
        
        Args:
            market_data: Dictionary containing market data from data providers
            
        Returns:
            Dictionary containing prepared input data
        """
        pass
    
    @abstractmethod
    def price(self, prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the pricing logic and return results.
        
        Args:
            prepared_data: Dictionary containing prepared input data
            
        Returns:
            Dictionary containing pricing results
        """
        pass
    
    @abstractmethod
    def calculate_greeks(self, prepared_data: Dict[str, Any], pricing_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate option Greeks (delta, gamma, vega, theta).
        
        Args:
            prepared_data: Dictionary containing prepared input data
            pricing_results: Dictionary containing pricing results
            
        Returns:
            Dictionary containing Greeks
        """
        pass
    
    def run_monte_carlo(self, prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for the option.
        Default implementation returns empty dict - override in models that support MC.
        
        Args:
            prepared_data: Dictionary containing prepared input data
            
        Returns:
            Dictionary containing Monte Carlo results
        """
        return {}
    
    def process(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the pricing request from start to finish.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary containing all pricing results
        """
        # Prepare input data
        prepared_data = self.prepare_input_data(market_data)
        
        # Execute pricing logic
        pricing_results = self.price(prepared_data)
        
        # Calculate Greeks
        greeks = self.calculate_greeks(prepared_data, pricing_results)
        
        # Run Monte Carlo if configured
        mc_results = {}
        if self.config.get('run_monte_carlo', False):
            mc_results = self.run_monte_carlo(prepared_data)
        
        # Assemble results
        results = {
            **pricing_results,
            'portfolio_greeks': greeks,
        }
        
        # Add Monte Carlo results if available
        if mc_results:
            results['mc_results'] = mc_results
        
        self.results = results
        return results
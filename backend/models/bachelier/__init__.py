"""
Bachelier option pricing model package.
"""

from .pricer import BachelierOptionPricer
from .mc_engine import MonteCarloSimulator

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from ..base import BasePricingModel

# Configure logging
logger = logging.getLogger(__name__)

class BachelierSpreadOptionModel(BasePricingModel):
    """
    Bachelier model implementation for spread options.
    
    This class adapts the BachelierOptionPricer to work with the pricing model factory pattern.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Bachelier spread option model.
        
        Args:
            config: Dictionary containing configuration parameters
        """
        super().__init__(config)
        self.pricer = BachelierOptionPricer()
        self.mc_simulator = MonteCarloSimulator(self.pricer)
        
        # Initialize data provider if needed
        self.data_provider = None
        if 'data_provider' in config:
            self.data_provider = config['data_provider']
        
    def prepare_input_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare the input data required for the Bachelier model.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Dictionary containing prepared input data
        """
        # Extract config parameters
        primary_index = self.config.get('primary_index')
        secondary_index = self.config.get('secondary_index')
        option_type = self.config.get('option_type', 'call')
        evaluation_date_str = self.config.get('evaluation_date')
        decision_days_prior = self.config.get('decision_days_prior', 0)
        first_delivery_month = self.config.get('first_delivery_month')
        first_delivery_year = self.config.get('first_delivery_year')
        delivery_day = self.config.get('delivery_day', 1)
        
        # Handle pricing method and differentials
        pricing_method = self.config.get('pricing_method', 'fixed_differential')
        primary_differential = self.config.get('primary_differential', 0.0)
        secondary_differential = self.config.get('secondary_differential', 0.0)
        total_cost_per_option = self.config.get('total_cost_per_option', 0.0)
        
        # Parse evaluation date
        if isinstance(evaluation_date_str, str):
            evaluation_date = datetime.strptime(evaluation_date_str, '%Y-%m-%d')
        else:
            evaluation_date = evaluation_date_str or datetime.now()
        
        # Calculate delivery dates
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month_idx = month_names.index(first_delivery_month) + 1
        delivery_date = datetime(first_delivery_year, month_idx, delivery_day)
        
        # Calculate decision date
        decision_date = delivery_date - timedelta(days=decision_days_prior)
        
        # Calculate time to maturity in years
        days_to_decision = (decision_date - evaluation_date).days
        time_to_maturity = max(0, days_to_decision / 365.0)
        
        # Extract market data
        forward_spreads = market_data.get('forward_spreads', [0.0])
        
        # Use spread_volatilities if available, otherwise fallback
        volatilities = market_data.get('spread_volatilities', [0.3])
        
        # Calculate strike price
        strike = secondary_differential - primary_differential + total_cost_per_option
        
        logger.info(f"Prepared input data for Bachelier model: "
                   f"S0={forward_spreads[0]}, K={strike}, T={time_to_maturity}, "
                   f"vol={volatilities[0]}, type={option_type}")
        
        return {
            'forward_spreads': forward_spreads,
            'volatilities': volatilities,
            'strike': strike,
            'time_to_maturity': time_to_maturity,
            'option_type': option_type,
            'evaluation_date': evaluation_date,
            'decision_date': decision_date,
            'delivery_date': delivery_date,
            'primary_differential': primary_differential,
            'secondary_differential': secondary_differential,
            'total_cost_per_option': total_cost_per_option
        }
    
    def price(self, prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Bachelier pricing logic.
        
        Args:
            prepared_data: Dictionary containing prepared input data
            
        Returns:
            Dictionary containing pricing results
        """
        # Extract prepared data
        forward_spread = prepared_data['forward_spreads'][0]
        volatility = prepared_data['volatilities'][0]
        strike = prepared_data['strike']
        time_to_maturity = prepared_data['time_to_maturity']
        option_type = prepared_data['option_type']
        delivery_date = prepared_data['delivery_date']
        
        # Calculate option value
        option_value = self.pricer.option_price(
            S0=forward_spread,
            K=strike,
            T=time_to_maturity,
            sigma=volatility,
            option_type=option_type
        )
        
        # Format the option date for the response
        option_date = delivery_date.strftime('%Y-%m-%d')
        
        return {
            'total_value': option_value,
            'option_values': {
                option_date: option_value
            },
            'forward_spreads': prepared_data['forward_spreads'],
            'volatilities': prepared_data['volatilities']
        }
    
    def calculate_greeks(self, prepared_data: Dict[str, Any], pricing_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate option Greeks for the Bachelier model.
        
        Args:
            prepared_data: Dictionary containing prepared input data
            pricing_results: Dictionary containing pricing results
            
        Returns:
            Dictionary containing Greeks
        """
        # Extract prepared data
        forward_spread = prepared_data['forward_spreads'][0]
        volatility = prepared_data['volatilities'][0]
        strike = prepared_data['strike']
        time_to_maturity = prepared_data['time_to_maturity']
        option_type = prepared_data['option_type']
        
        # Calculate Greeks
        delta = self.pricer.delta(
            S0=forward_spread,
            K=strike,
            T=time_to_maturity,
            sigma=volatility,
            option_type=option_type
        )
        
        gamma = self.pricer.gamma(
            S0=forward_spread,
            K=strike,
            T=time_to_maturity,
            sigma=volatility,
            option_type=option_type
        )
        
        vega = self.pricer.vega(
            S0=forward_spread,
            K=strike,
            T=time_to_maturity,
            sigma=volatility,
            option_type=option_type
        )
        
        theta = self.pricer.theta(
            S0=forward_spread,
            K=strike,
            T=time_to_maturity,
            sigma=volatility,
            option_type=option_type
        )
        
        # Calculate differential delta if needed
        differential_delta = self.pricer.differential_delta(
            S0=forward_spread,
            K=strike,
            T=time_to_maturity,
            sigma=volatility,
            option_type=option_type
        )
        
        return {
            'delta': delta,
            'gamma': gamma,
            'vega': vega,
            'theta': theta,
            'differential_delta': differential_delta
        }
    
    def run_monte_carlo(self, prepared_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for the Bachelier model.
        
        Args:
            prepared_data: Dictionary containing prepared input data
            
        Returns:
            Dictionary containing Monte Carlo results
        """
        # Extract prepared data
        forward_spread = prepared_data['forward_spreads'][0]
        volatility = prepared_data['volatilities'][0]
        strike = prepared_data['strike']
        time_to_maturity = prepared_data['time_to_maturity']
        option_type = prepared_data['option_type']
        
        # Monte Carlo parameters
        num_paths = self.config.get('mc_paths', 10000)
        num_steps = max(1, int(time_to_maturity * 252))  # 252 trading days per year
        seed = self.config.get('mc_seed', 42)
        
        # Run simulation
        mc_results = self.mc_simulator.run_simulation(
            forward_spread=forward_spread,
            volatility=volatility,
            time_to_maturity=time_to_maturity,
            strike=strike,
            option_type=option_type,
            num_paths=num_paths,
            num_steps=num_steps,
            seed=seed
        )
        
        return mc_results
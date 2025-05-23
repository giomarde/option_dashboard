"""
Monte Carlo simulator for the Bachelier model.
"""

import numpy as np
from typing import Dict, List, Optional, Union, Tuple

class MonteCarloSimulator:
    """
    Monte Carlo simulator for spread options using the Bachelier model.
    """
    
    def __init__(self, pricer):
        """
        Initialize the simulator with a pricer.
        
        Args:
            pricer: Option pricer instance
        """
        self.pricer = pricer
    
    def simulate_paths(self, S0, vol, T, num_paths, num_steps, seed=None):
        """
        Simulate price paths using Bachelier model.
        
        Args:
            S0 (float): Initial price
            vol (float): Volatility
            T (float): Time horizon in years
            num_paths (int): Number of paths to simulate
            num_steps (int): Number of time steps
            seed (int): Random seed for reproducibility
            
        Returns:
            np.array: Simulated price paths
        """
        if seed is not None:
            np.random.seed(seed)
        
        dt = T / num_steps
        paths = np.zeros((num_paths, num_steps + 1))
        paths[:, 0] = S0
        
        for t in range(1, num_steps + 1):
            z = np.random.normal(0, 1, num_paths)
            paths[:, t] = paths[:, t-1] + vol * np.sqrt(dt) * z
        
        return paths
    
    def run_simulation(self, forward_spread, volatility, time_to_maturity, strike, 
                      option_type='call', r=0, num_paths=10000, num_steps=50, seed=None):
        """
        Run Monte Carlo simulation for a spread option.
        
        Args:
            forward_spread (float): Current forward spread
            volatility (float): Volatility of the spread
            time_to_maturity (float): Time to maturity in years
            strike (float): Strike price
            option_type (str): 'call' or 'put'
            r (float): Risk-free rate
            num_paths (int): Number of paths to simulate
            num_steps (int): Number of time steps
            seed (int): Random seed for reproducibility
            
        Returns:
            dict: Monte Carlo simulation results
        """
        # Simulate paths
        paths = self.simulate_paths(
            S0=forward_spread,
            vol=volatility,
            T=time_to_maturity,
            num_paths=num_paths,
            num_steps=num_steps,
            seed=seed
        )
        
        # Calculate payoffs at maturity
        final_values = paths[:, -1]
        if option_type.lower() == 'call':
            payoffs = np.maximum(0, final_values - strike)
        else:  # put option
            payoffs = np.maximum(0, strike - final_values)
        
        # Discount payoffs
        discount_factor = np.exp(-r * time_to_maturity)
        option_values = discount_factor * payoffs
        
        # Calculate statistics
        mean_value = np.mean(option_values)
        std_dev = np.std(option_values)
        
        # Calculate percentiles
        percentiles = {
            5: np.percentile(option_values, 5),
            25: np.percentile(option_values, 25),
            50: np.percentile(option_values, 50),
            75: np.percentile(option_values, 75),
            95: np.percentile(option_values, 95)
        }
        
        # Calculate exercise probabilities
        if option_type.lower() == 'call':
            exercise_prob = np.mean(final_values > strike)
        else:
            exercise_prob = np.mean(final_values < strike)
        
        return {
            'summary_statistics': {
                'mean': mean_value,
                'std': std_dev,
                'std_error': std_dev / np.sqrt(num_paths),
                'percentiles': percentiles
            },
            'exercise_statistics': {
                'exercise_probabilities': [{
                    'primary': exercise_prob,
                    'secondary': 1 - exercise_prob
                }]
            },
            'paths': paths.tolist()  # Convert to list for JSON serialization
        }
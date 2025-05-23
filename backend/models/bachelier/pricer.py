"""
Bachelier option pricing model implementation.
"""

import numpy as np
from scipy.stats import norm

class BachelierOptionPricer:
    """
    Class for pricing options using the Bachelier (normal) model, particularly
    suitable for spread options where the underlying can be negative.
    """
    
    def __init__(self):
        pass
    
    def option_price(self, S0, K, T, sigma, option_type='call', r=0):
        """
        Calculates the price of European option under Bachelier model
        
        Args:
            S0 (float): Current value of the underlying asset (or spread)
            K (float): Strike price
            T (float): Time to maturity in years
            sigma (float): Volatility of the underlying
            option_type (str): 'call' or 'put'
            r (float): Risk-free rate (typically set to 0 for commodities)
            
        Returns:
            float: Option price
        """
        # Discount factor
        df = np.exp(-r * T)
        
        # Calculate d
        if sigma * np.sqrt(T) > 0:
            d = (S0 - K) / (sigma * np.sqrt(T))
        else:
            # Handle the case when T is very small or sigma is zero
            if option_type.lower() == 'call':
                return max(0, S0 - K)
            else:
                return max(0, K - S0)
        
        # Standard normal CDF and PDF
        Nd = norm.cdf(d)
        nd = norm.pdf(d)
        
        # Option price calculation
        if option_type.lower() == 'call':
            price = df * ((S0 - K) * Nd + sigma * np.sqrt(T) * nd)
        else:  # put option
            price = df * ((K - S0) * (1 - Nd) + sigma * np.sqrt(T) * nd)
            
        return price
    
    def delta(self, S0, K, T, sigma, option_type='call', r=0):
        """
        Calculates the delta of European option under Bachelier model
        
        Args:
            S0 (float): Current value of the underlying asset (or spread)
            K (float): Strike price
            T (float): Time to maturity in years
            sigma (float): Volatility of the underlying
            option_type (str): 'call' or 'put'
            r (float): Risk-free rate
            
        Returns:
            float: Option delta
        """
        df = np.exp(-r * T)
        
        if sigma * np.sqrt(T) <= 0:
            # Edge case
            if option_type.lower() == 'call':
                return 1.0 if S0 > K else 0.0
            else:
                return -1.0 if S0 < K else 0.0
        
        d = (S0 - K) / (sigma * np.sqrt(T))
        
        if option_type.lower() == 'call':
            return df * norm.cdf(d)
        else:  # put option
            return df * (norm.cdf(d) - 1)

    def differential_delta(self, S0, K, T, sigma, option_type='call', r=0):
        """
        Calculates the sensitivity of the option price to changes in the differential
        
        Args:
            S0 (float): Current value of the underlying asset (or spread)
            K (float): Strike price
            T (float): Time to maturity in years
            sigma (float): Volatility of the underlying
            option_type (str): 'call' or 'put'
            r (float): Risk-free rate
            
        Returns:
            float: Differential delta (sensitivity to changes in the differential)
        """
        df = np.exp(-r * T)
        
        if sigma * np.sqrt(T) <= 0:
            # Edge case
            if option_type.lower() == 'call':
                return -1.0 if S0 > K else 0.0
            else:
                return 1.0 if S0 < K else 0.0
        
        d = (S0 - K) / (sigma * np.sqrt(T))
        
        # For a call option, when secondary differential increases, strike increases, reducing value
        # For a put option, when secondary differential increases, strike increases, increasing value
        if option_type.lower() == 'call':
            return -df * norm.cdf(d)  # Negative of regular delta
        else:  # put option
            return -df * (norm.cdf(d) - 1)  # Negative of regular delta
            
    def gamma(self, S0, K, T, sigma, option_type='call', r=0):
        """
        Calculates the gamma of European option under Bachelier model
        """
        df = np.exp(-r * T)
        
        if sigma * np.sqrt(T) <= 0:
            return 0.0
        
        d = (S0 - K) / (sigma * np.sqrt(T))
        pdf_d = norm.pdf(d)
        denom = sigma * np.sqrt(T)
        
        gamma = df * pdf_d / denom
        
        return gamma
    
    def vega(self, S0, K, T, sigma, option_type='call', r=0):
        """
        Calculates the vega of European option under Bachelier model
        
        Args:
            S0 (float): Current value of the underlying asset (or spread)
            K (float): Strike price
            T (float): Time to maturity in years
            sigma (float): Volatility of the underlying
            option_type (str): 'call' or 'put'
            r (float): Risk-free rate
            
        Returns:
            float: Option vega (same for call and put)
        """
        df = np.exp(-r * T)
        
        if T <= 0:
            return 0.0  # Edge case
        
        d = (S0 - K) / (sigma * np.sqrt(T))
        
        # Vega is the same for call and put
        return df * norm.pdf(d) * np.sqrt(T)
    
    def theta(self, S0, K, T, sigma, option_type='call', r=0):
        """
        Calculates the theta of European option under Bachelier model
        
        Args:
            S0 (float): Current value of the underlying asset (or spread)
            K (float): Strike price
            T (float): Time to maturity in years
            sigma (float): Volatility of the underlying
            option_type (str): 'call' or 'put'
            r (float): Risk-free rate
            
        Returns:
            float: Option theta
        """
        df = np.exp(-r * T)
        
        if T <= 0:
            return 0.0  # Edge case
        
        d = (S0 - K) / (sigma * np.sqrt(T))
        
        # Common term
        common_term = -sigma * norm.pdf(d) / (2 * np.sqrt(T))
        
        if option_type.lower() == 'call':
            return df * (common_term + r * (S0 - K) * norm.cdf(d))
        else:  # put option
            return df * (common_term + r * (K - S0) * norm.cdf(-d))
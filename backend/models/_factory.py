"""
Factory module for pricing models.
"""

import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

def get_pricing_model(config: Dict[str, Any]):
    """
    Factory function to get the appropriate pricing model based on configuration.
    
    Args:
        config: Dictionary containing configuration parameters
        
    Returns:
        An instance of a BasePricingModel subclass
    """
    model_type = config.get('pricing_model', 'bachelier')
    option_type = config.get('option_type', 'vanilla_spread')
    
    logger.info(f"Instantiating {model_type} model for {option_type} option")
    
    # Import here to avoid circular imports
    if model_type == 'bachelier':
        from .bachelier import BachelierSpreadOptionModel
        return BachelierSpreadOptionModel(config)
    elif model_type == 'dempster':
        # Placeholder for future implementation
        from .bachelier import BachelierSpreadOptionModel
        logger.warning("Dempster model not implemented yet, using Bachelier as fallback")
        return BachelierSpreadOptionModel(config)
    elif model_type == 'miltersen':
        # Placeholder for future implementation
        from .bachelier import BachelierSpreadOptionModel
        logger.warning("Miltersen model not implemented yet, using Bachelier as fallback")
        return BachelierSpreadOptionModel(config)
    else:
        logger.warning(f"Unknown model type {model_type}, using Bachelier as fallback")
        from .bachelier import BachelierSpreadOptionModel
        return BachelierSpreadOptionModel(config)
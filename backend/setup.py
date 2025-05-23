"""
Setup script for the option pricing backend.
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_requirements_file():
    """Create a requirements.txt file with required packages."""
    requirements = [
        "flask==2.0.1",
        "flask-cors==3.0.10",
        "numpy==1.23.0",
        "pandas==1.5.3",
        "scipy==1.9.1",
        "matplotlib==3.6.3",
        "arch==5.0.0",  # For volatility modeling
    ]
    
    with open('requirements.txt', 'w') as f:
        f.write('\n'.join(requirements))
    
    logger.info("Created requirements.txt")

def install_requirements():
    """Install required packages."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                      check=True)
        logger.info("Installed required packages")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error installing packages: {e}")
        return False
    
    return True

def create_directory_structure():
    """Create the necessary directory structure."""
    # Define directories to create
    directories = [
        'data',
        'models',
        'models/bachelier',
        'models/volatility',
        'processors',
    ]
    
    # Create directories
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created directory: {directory}")
        
        # Create __init__.py files
        init_file = os.path.join(directory, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                pass
    
    return True

if __name__ == "__main__":
    logger.info("Setting up the option pricing backend...")
    
    # Create directory structure
    create_directory_structure()
    
    # Create requirements file
    create_requirements_file()
    
    # Install requirements
    install_requirements()
    
    logger.info("Setup complete!")
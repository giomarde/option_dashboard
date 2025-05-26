# backend/data_feed/csv_provider.py
"""
CSV Data Feed Provider - Updated with improved data loading and error handling

Implementation of the data feed provider interface using CSV files.
"""

import pandas as pd
import os
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Union
import numpy as np

from .base import DataFeedProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CSVDataFeedProvider(DataFeedProvider):
    """
    Data feed provider that uses CSV files as the data source
    """
    
    def __init__(self, data_folder='data'):
        """
        Initialize the CSV data provider
        
        Args:
            data_folder: Path to the folder containing CSV data files
        """
        # Handle both relative and absolute paths
        if os.path.isabs(data_folder):
            self.data_folder = data_folder
        else:
            # If relative path, make it relative to the backend directory
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_folder = os.path.join(backend_dir, data_folder)
        
        logger.info(f"CSV Data Provider initialized with path: {self.data_folder}")
        
        # Make sure the data folder exists
        if not os.path.exists(self.data_folder):
            logger.warning(f"Data folder '{self.data_folder}' does not exist. Creating it.")
            os.makedirs(self.data_folder, exist_ok=True)
        
        # Log the contents of the data folder for debugging
        if os.path.exists(self.data_folder):
            files = [f for f in os.listdir(self.data_folder) if f.endswith('.csv')]
            logger.info(f"Found {len(files)} CSV files in data folder: {files}")
        else:
            logger.warning(f"Data folder does not exist: {self.data_folder}")
    
    def _get_base_ticker(self, ticker):
        """
        Extract base ticker for CSV lookup
        
        Args:
            ticker: The full ticker symbol
            
        Returns:
            str: The base ticker without month/suffix info
        """
        # Remove ' Comdty' suffix if present
        cleaned_ticker = ticker.replace(' Comdty', '')
        
        # Check if the ticker contains month info (e.g., NWL1 or NWL_M01)
        if '_M' in cleaned_ticker:
            # For new format like NWL_M01, extract the base ticker
            base = cleaned_ticker.split('_M')[0]
            return base
        elif cleaned_ticker.startswith('THE') or cleaned_ticker.startswith('TFU') or cleaned_ticker.startswith('DES'):
            # Special case for THE and DES
            if cleaned_ticker.startswith('THE'):
                return 'THE'
            elif cleaned_ticker.startswith('TFU'):
                return 'TFU'
            else:
                return 'DES'
        else:
            # For old format like NWL1, extract letters before numbers
            base = ""
            for char in cleaned_ticker:
                if char.isalpha():
                    base += char
                else:
                    break
            return base if base else cleaned_ticker
    
    def _convert_to_new_id_format(self, ticker):
        """
        Convert any ticker format to the new ID format (Index_Mxx)
        
        Args:
            ticker: The ticker symbol in any format
            
        Returns:
            str: The ticker in the new ID format
        """
        # Remove ' Comdty' suffix if present
        cleaned_ticker = ticker.replace(' Comdty', '')
        
        # If already in new format, return as is
        if '_M' in cleaned_ticker:
            return cleaned_ticker
        
        # Handle special cases for THE, TFU and DES
        if cleaned_ticker.startswith('THE') and len(cleaned_ticker) > 3 and cleaned_ticker[3:].isdigit():
            month_num = int(cleaned_ticker[3:])
            return f"THE_M{month_num:02d}"
        elif cleaned_ticker.startswith('TFU') and len(cleaned_ticker) > 3 and cleaned_ticker[3:].isdigit():
            month_num = int(cleaned_ticker[3:])
            return f"TFU_M{month_num:02d}"
        elif cleaned_ticker.startswith('DES') and len(cleaned_ticker) > 3 and cleaned_ticker[3:].isdigit():
            month_num = int(cleaned_ticker[3:])
            return f"DES_M{month_num:02d}"
        else:
            # For regular tickers like NWL1, JKM1, extract base and month number
            base = ""
            month_str = ""
            
            for char in cleaned_ticker:
                if char.isalpha():
                    base += char
                elif char.isdigit():
                    month_str += char
            
            if base and month_str:
                month_num = int(month_str)
                return f"{base}_M{month_num:02d}"
            
            # If no clear pattern, return as is
            return cleaned_ticker
    
    def _load_csv_data(self, base_ticker, verbose=False):
        """
        Load CSV data with improved error handling and logging
        
        Args:
            base_ticker: The base ticker to load data for
            verbose: Whether to print verbose debug info
            
        Returns:
            DataFrame or None: The loaded CSV data or None if not found
        """
        csv_path = os.path.join(self.data_folder, f"{base_ticker}.csv")
        
        if verbose:
            logger.info(f"Attempting to load data from: {csv_path}")
        
        if not os.path.exists(csv_path):
            if verbose:
                logger.warning(f"CSV file not found: {csv_path}")
            return None
        
        try:
            # Try to load the CSV file
            df = pd.read_csv(csv_path)
            
            if verbose:
                logger.info(f"Successfully loaded CSV with shape: {df.shape}")
                logger.info(f"Columns: {df.columns.tolist()}")
                if len(df) > 0:
                    logger.info(f"First few rows: {df.head(3)}")
            
            # Convert DATE column if it exists
            if 'DATE' in df.columns:
                df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
            
            return df
        except Exception as e:
            logger.error(f"Error loading CSV file {csv_path}: {e}")
            return None
    
    def fetch_data(self, ticker: str, start_date: Union[str, date, datetime], 
                  end_date: Union[str, date, datetime], field: str = 'PX_LAST',
                  verbose: bool = False) -> pd.Series:
        """
        Fetch price data for a specific ticker from CSV with improved fallback behavior
        
        Args:
            ticker: The ticker symbol
            start_date: Start date for the data range
            end_date: End date for the data range
            field: The field to fetch (not used in CSV implementation)
            verbose: Whether to print verbose debug info
            
        Returns:
            pd.Series: A pandas Series with dates as index and prices as values
        """
        if verbose:
            logger.info(f"Fetching data for: {ticker}")
        
        # Get the base ticker
        base_ticker = self._get_base_ticker(ticker)
        expected_id = self._convert_to_new_id_format(ticker)
        
        if verbose:
            logger.info(f"Base ticker: {base_ticker}, Expected ID: {expected_id}")
        
        # Load the CSV data
        df = self._load_csv_data(base_ticker, verbose)
        
        if df is None:
            # Try alternative approach - the file might exist with a different name
            # List available CSV files
            available_files = [f for f in os.listdir(self.data_folder) if f.endswith('.csv')]
            
            if verbose:
                logger.info(f"Looking for alternative files. Available files: {available_files}")
            
            # Check for files that might contain the ticker data
            for file in available_files:
                try:
                    test_df = pd.read_csv(os.path.join(self.data_folder, file))
                    if 'ID' in test_df.columns and expected_id in test_df['ID'].values:
                        df = test_df
                        logger.info(f"Found {expected_id} in alternative file: {file}")
                        break
                except Exception:
                    continue
        
        if df is None:
            # Still no data found, raise error
            raise ValueError(f"No data found for {ticker} in {self.data_folder}")
        
        # Convert dates for filtering
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Set up filtering conditions
        has_date = 'DATE' in df.columns
        has_id = 'ID' in df.columns
        
        if has_date:
            # Filter by date
            df = df[(df['DATE'] >= start_dt) & (df['DATE'] <= end_dt)]
            
            if verbose:
                logger.info(f"After date filter: {len(df)} rows")
        
        if has_id:
            # Filter by ID
            df = df[df['ID'] == expected_id]
            
            if verbose:
                logger.info(f"After ID filter: {len(df)} rows")
        
        # Check if we have data after filtering
        if len(df) == 0:
            # Fall back to general ticker data if specific month contract not found
            if '_M' in expected_id:
                # Try to find data for the base ticker instead
                base_id = expected_id.split('_M')[0]
                
                if has_id and base_id in df['ID'].values:
                    df = df[df['ID'] == base_id]
                    logger.info(f"Using base ticker {base_id} data as fallback for {expected_id}")
                else:
                    # As a last resort, create synthetic data
                    logger.warning(f"No data found for {expected_id} or {base_id}, generating synthetic data")
                    dates = pd.date_range(start=start_dt, end=end_dt, freq='B')
                    synthetic_price = 10.0  # Default price
                    df = pd.DataFrame({
                        'DATE': dates,
                        'PRICE': np.random.normal(synthetic_price, synthetic_price * 0.01, len(dates))
                    })
                    df = df.set_index('DATE')
                    return df['PRICE']
        
        # Return PRICE series if we have data
        if len(df) > 0 and 'PRICE' in df.columns:
            # Remove duplicates by taking the last value for each date
            if has_date:
                df = df.drop_duplicates(subset=['DATE'], keep='last')
                df = df.set_index('DATE')
            
            if verbose:
                logger.info(f"Returning {len(df)} price points")
                if len(df) > 0:
                    logger.info(f"Price range: {df['PRICE'].min():.4f} to {df['PRICE'].max():.4f}")
            
            return df['PRICE']
        
        # If we reach here, we couldn't find appropriate data
        logger.error(f"No usable data found for {ticker} after filtering")
        raise ValueError(f"No data found for {ticker} in {self.data_folder}")
    
    def fetch_forward_curve(self, base_ticker: str, num_months: int = 12,
                        curve_date: Optional[Union[str, date, datetime]] = None) -> pd.DataFrame:
        """
        Fetch forward curve for a base ticker from CSV with improved fallback behavior
        
        Args:
            base_ticker: The base ticker symbol
            num_months: Number of months to fetch in the forward curve
            curve_date: The pricing date - we'll look for the most recent data before this date
                
        Returns:
            pd.DataFrame: A dataframe with forward curve data
        """
        pricing_date = datetime.now() if curve_date is None else pd.to_datetime(curve_date)
        
        logger.info(f"Fetching forward curve for {base_ticker} using most recent data before {pricing_date}")
        
        # Initialize the forward curve data
        fwd_data = {}
        
        # First try forward curve CSV
        fc_path = os.path.join(self.data_folder, f"{base_ticker}_forward_curve.csv")
        if os.path.exists(fc_path):
            try:
                logger.info(f"Found forward curve file: {fc_path}")
                fc_df = pd.read_csv(fc_path)
                if 'DATE' in fc_df.columns:
                    fc_df['DATE'] = pd.to_datetime(fc_df['DATE'])
                    
                    # Filter to dates before or equal to pricing_date
                    fc_df = fc_df[fc_df['DATE'] <= pricing_date]
                    
                    if len(fc_df) > 0:
                        # Get the most recent date in the filtered data
                        most_recent_date = fc_df['DATE'].max()
                        most_recent_row = fc_df[fc_df['DATE'] == most_recent_date].iloc[0]
                        
                        for i in range(1, num_months + 1):
                            month_code = f"M{i:02d}"
                            if month_code in most_recent_row:
                                fwd_data[month_code] = most_recent_row[month_code]
                                
                        if fwd_data:
                            logger.info(f"Successfully loaded forward curve data: {len(fwd_data)} months from {most_recent_date}")
                            return pd.DataFrame([fwd_data], index=[most_recent_date])
            except Exception as e:
                logger.error(f"Forward curve CSV failed: {e}")
        
        # Fetch individual months
        logger.info(f"Fetching individual month contracts for {base_ticker}")
        valid_prices_found = 0
        
        for i in range(1, num_months + 1):
            month_code = f"M{i:02d}"
            
            # Construct specific contract ticker using new format
            ticker = f"{base_ticker}_{month_code}"
            
            try:
                # Use verbose mode for the first month to help diagnose issues
                verbose = (i == 1)
                price = self.fetch_data(ticker, curve_date, curve_date, verbose=verbose)
                if isinstance(price, pd.Series) and len(price) > 0:
                    fwd_data[month_code] = price.iloc[0]
                    logger.info(f"Found price for {ticker}: {price.iloc[0]:.4f}")
                    valid_prices_found += 1
                else:
                    logger.warning(f"No data for {ticker} on {curve_date}")
                    # Use synthetic data as fallback
                    base_price = 10.0 + (i - 1) * 0.1  # Slightly increasing forward curve
                    fwd_data[month_code] = base_price
            except Exception as e:
                logger.warning(f"Error fetching {ticker}: {str(e)}")
                # Use synthetic data as fallback
                base_price = 10.0 + (i - 1) * 0.1  # Slightly increasing forward curve
                fwd_data[month_code] = base_price
        
        logger.info(f"Forward curve constructed with {valid_prices_found} valid prices")
        return pd.DataFrame([fwd_data], index=[curve_date])
    
    def fetch_market_data(self, ticker: str, date: Optional[Union[str, date, datetime]] = None) -> Dict:
        """
        Fetch latest market data for a ticker from CSV with improved fallback behavior
        
        Args:
            ticker: The ticker symbol
            date: The pricing date - we'll look for the most recent data before this date
                
        Returns:
            Dict: A dictionary with market data (price, last_updated)
        """
        pricing_date = datetime.now() if date is None else pd.to_datetime(date)
        
        try:
            # Get the base ticker
            base_ticker = self._get_base_ticker(ticker)
            expected_id = self._convert_to_new_id_format(ticker)
            
            # Load the CSV data
            df = self._load_csv_data(base_ticker)
            
            if df is not None and 'DATE' in df.columns:
                # Convert dates and filter
                df['DATE'] = pd.to_datetime(df['DATE'])
                df = df[df['DATE'] <= pricing_date]
                
                if len(df) > 0:
                    # Get the most recent date
                    most_recent_date = df['DATE'].max()
                    recent_data = df[df['DATE'] == most_recent_date]
                    
                    # Filter by ID if available
                    if 'ID' in recent_data.columns:
                        if expected_id in recent_data['ID'].values:
                            recent_data = recent_data[recent_data['ID'] == expected_id]
                        elif base_ticker in recent_data['ID'].values:
                            recent_data = recent_data[recent_data['ID'] == base_ticker]
                    
                    if len(recent_data) > 0 and 'PRICE' in recent_data.columns:
                        price = recent_data['PRICE'].iloc[0]
                        return {
                            "price": float(price),
                            "lastUpdated": most_recent_date.strftime('%Y-%m-%d')
                        }
            
            # Generate synthetic data as fallback
            logger.warning(f"No historical data found for {ticker}, using synthetic price")
            synthetic_price = 10.0
            return {
                "price": synthetic_price,
                "lastUpdated": pricing_date.strftime('%Y-%m-%d')
            }
                    
        except Exception as e:
            logger.error(f"Error fetching market data for {ticker}: {e}")
            # Return synthetic data as fallback
            synthetic_price = 10.0
            return {
                "price": synthetic_price,
                "lastUpdated": pricing_date.strftime('%Y-%m-%d')
            }
    
    def fetch_volatility_surface(self, primary_ticker: str, secondary_ticker: Optional[str] = None,
                               date: Optional[Union[str, date, datetime]] = None) -> Dict:
        """
        Fetch volatility surface data from CSV with improved fallback behavior
        
        Args:
            primary_ticker: The primary ticker symbol
            secondary_ticker: Optional secondary ticker for spread volatilities
            date: The date for which to fetch volatility data
            
        Returns:
            Dict: A dictionary with volatility surface data
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
            
        result = {}
        
        # Try to load volatility data from CSV
        base_primary = self._get_base_ticker(primary_ticker)
        vol_path = os.path.join(self.data_folder, f"{base_primary}_volatility.csv")
        
        primary_vol = 0.3  # Default volatility if not found
        
        if os.path.exists(vol_path):
            try:
                vol_df = pd.read_csv(vol_path)
                if 'DATE' in vol_df.columns and 'VOLATILITY' in vol_df.columns:
                    vol_df['DATE'] = pd.to_datetime(vol_df['DATE'])
                    date_dt = pd.to_datetime(date)
                    closest_idx = (vol_df['DATE'] - date_dt).abs().idxmin()
                    primary_vol = vol_df.iloc[closest_idx]['VOLATILITY']
            except Exception as e:
                logger.error(f"Error reading volatility data: {e}")
        
        # Get current price for the primary ticker
        try:
            primary_price = self.fetch_market_data(primary_ticker, date)['price']
        except:
            primary_price = 10.0  # Default price if not found
        
        # Generate primary smile
        primary_smile = [
            {"strike": 0.8 * primary_price, "volatility": primary_vol * 1.1},
            {"strike": 0.9 * primary_price, "volatility": primary_vol * 1.05},
            {"strike": primary_price, "volatility": primary_vol},
            {"strike": 1.1 * primary_price, "volatility": primary_vol * 1.05},
            {"strike": 1.2 * primary_price, "volatility": primary_vol * 1.1}
        ]
        
        result["primary"] = primary_smile
        
        # If we have a secondary ticker, generate data for it as well
        if secondary_ticker:
            base_secondary = self._get_base_ticker(secondary_ticker)
            sec_vol_path = os.path.join(self.data_folder, f"{base_secondary}_volatility.csv")
            
            secondary_vol = 0.25  # Default volatility if not found
            
            if os.path.exists(sec_vol_path):
                try:
                    vol_df = pd.read_csv(sec_vol_path)
                    if 'DATE' in vol_df.columns and 'VOLATILITY' in vol_df.columns:
                        vol_df['DATE'] = pd.to_datetime(vol_df['DATE'])
                        date_dt = pd.to_datetime(date)
                        closest_idx = (vol_df['DATE'] - date_dt).abs().idxmin()
                        secondary_vol = vol_df.iloc[closest_idx]['VOLATILITY']
                except Exception as e:
                    logger.error(f"Error reading secondary volatility data: {e}")
            
            # Get current price for the secondary ticker
            try:
                secondary_price = self.fetch_market_data(secondary_ticker, date)['price']
            except:
                secondary_price = 9.5  # Default price if not found
            
            # Generate secondary smile
            secondary_smile = [
                {"strike": 0.8 * secondary_price, "volatility": secondary_vol * 1.1},
                {"strike": 0.9 * secondary_price, "volatility": secondary_vol * 1.05},
                {"strike": secondary_price, "volatility": secondary_vol},
                {"strike": 1.1 * secondary_price, "volatility": secondary_vol * 1.05},
                {"strike": 1.2 * secondary_price, "volatility": secondary_vol * 1.1}
            ]
            
            result["secondary"] = secondary_smile
            
            # Generate spread smile
            spread = primary_price - secondary_price
            spread_vol = (primary_vol + secondary_vol) / 2  # Simple approximation
            
            spread_smile = [
                {"strike": spread - 0.4, "volatility": spread_vol * 1.15},
                {"strike": spread - 0.2, "volatility": spread_vol * 1.05},
                {"strike": spread, "volatility": spread_vol},
                {"strike": spread + 0.2, "volatility": spread_vol * 1.05},
                {"strike": spread + 0.4, "volatility": spread_vol * 1.15}
            ]
            
            result["spread"] = spread_smile
        
        return result
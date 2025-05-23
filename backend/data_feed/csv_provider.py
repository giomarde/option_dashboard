# backend/data_feed/csv_provider.py
"""
CSV Data Feed Provider - Updated with proper path handling

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
        elif cleaned_ticker.startswith('THE') or cleaned_ticker.startswith('DES'):
            # Special case for THE and DES
            if cleaned_ticker.startswith('THE'):
                return 'THE'
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
        
        # Handle special cases for THE and DES
        if cleaned_ticker.startswith('THE') and len(cleaned_ticker) > 3 and cleaned_ticker[3:].isdigit():
            month_num = int(cleaned_ticker[3:])
            return f"THE_M{month_num:02d}"
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
    
    def fetch_data(self, ticker: str, start_date: Union[str, date, datetime], 
                  end_date: Union[str, date, datetime], field: str = 'PX_LAST',
                  verbose: bool = False) -> pd.Series:
        """
        Fetch price data for a specific ticker from CSV
        
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
        
        # Get the CSV file based on base ticker
        base_ticker = self._get_base_ticker(ticker)
        csv_path = os.path.join(self.data_folder, f"{base_ticker}.csv")
        
        if verbose:
            logger.info(f"Looking for CSV file: {csv_path}")
            logger.info(f"File exists: {os.path.exists(csv_path)}")
        
        # Try CSV lookup
        if os.path.exists(csv_path):
            if verbose:
                logger.info(f"Loading from {csv_path}")
            
            try:
                df = pd.read_csv(csv_path)
                
                if verbose:
                    logger.info(f"Raw data shape: {df.shape}")
                    logger.info(f"Columns: {df.columns.tolist()}")
                    if len(df) > 0:
                        logger.info(f"Sample of first few rows:")
                        logger.info(df.head())
                
                # Convert DATE column
                df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
                
                # Filter by date range first
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df = df[(df['DATE'] >= start_dt) & (df['DATE'] <= end_dt)]
                
                if verbose:
                    logger.info(f"After date filter ({start_dt} to {end_dt}): {len(df)} rows")
                
                # Convert ticker to the new ID format for filtering
                expected_id = self._convert_to_new_id_format(ticker)
                
                if verbose:
                    logger.info(f"Expected ID format: {expected_id}")
                
                if 'ID' in df.columns:
                    # Show unique IDs for debugging
                    if verbose and len(df) > 0:
                        unique_ids = df['ID'].unique()
                        logger.info(f"Available IDs in CSV: {unique_ids}")
                    
                    df = df[df['ID'] == expected_id]
                    
                    if verbose:
                        logger.info(f"Filtered to ID={expected_id}: {len(df)} rows")
                
                # Return PRICE series if we have data
                if len(df) > 0 and 'PRICE' in df.columns:
                    # Remove duplicates by taking the last value for each date
                    df = df.drop_duplicates(subset=['DATE'], keep='last')
                    df = df.set_index('DATE')
                    if verbose:
                        logger.info(f"Returning {len(df)} price points")
                        logger.info(f"Price range: {df['PRICE'].min():.4f} to {df['PRICE'].max():.4f}")
                    return df['PRICE']
                else:
                    if verbose:
                        logger.info(f"No data after filtering. Available columns: {df.columns.tolist()}")
                        
            except Exception as e:
                logger.error(f"CSV read failed: {e}")
                if verbose:
                    import traceback
                    traceback.print_exc()
        else:
            if verbose:
                logger.info(f"File not found: {csv_path}")
                # List available files for debugging
                if os.path.exists(self.data_folder):
                    available_files = [f for f in os.listdir(self.data_folder) if f.endswith('.csv')]
                    logger.info(f"Available CSV files: {available_files}")
        
        # Nothing found
        raise ValueError(f"No data found for {ticker} in {csv_path}")
    
    def fetch_forward_curve(self, base_ticker: str, num_months: int = 12,
                           curve_date: Optional[Union[str, date, datetime]] = None) -> pd.DataFrame:
        """
        Fetch forward curve for a base ticker from CSV
        
        Args:
            base_ticker: The base ticker symbol
            num_months: Number of months to fetch in the forward curve
            curve_date: The date for which to fetch the forward curve
            
        Returns:
            pd.DataFrame: A dataframe with forward curve data
        """
        if curve_date is None:
            curve_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching forward curve for {base_ticker} on {curve_date}")
        
        fwd_data = {}
        
        # First try forward curve CSV
        fc_path = os.path.join(self.data_folder, f"{base_ticker}_forward_curve.csv")
        if os.path.exists(fc_path):
            try:
                logger.info(f"Found forward curve file: {fc_path}")
                fc_df = pd.read_csv(fc_path)
                if 'DATE' in fc_df.columns:
                    fc_df['DATE'] = pd.to_datetime(fc_df['DATE'])
                    date_dt = pd.to_datetime(curve_date)
                    closest_idx = (fc_df['DATE'] - date_dt).abs().idxmin()
                    row = fc_df.iloc[closest_idx]
                    
                    for i in range(1, num_months + 1):
                        month_code = f"M{i:02d}"
                        if month_code in row:
                            fwd_data[month_code] = row[month_code]
                            
                    if fwd_data:
                        logger.info(f"Successfully loaded forward curve data: {len(fwd_data)} months")
                        return pd.DataFrame([fwd_data], index=[curve_date])
            except Exception as e:
                logger.error(f"Forward curve CSV failed: {e}")
        
        # Fetch individual months
        logger.info(f"Fetching individual month contracts for {base_ticker}")
        for i in range(1, num_months + 1):
            month_code = f"M{i:02d}"
            
            # Construct specific contract ticker using new format
            ticker = f"{base_ticker}_{month_code}"
            
            try:
                price = self.fetch_data(ticker, curve_date, curve_date, verbose=False)
                if isinstance(price, pd.Series) and len(price) > 0:
                    fwd_data[month_code] = price.iloc[0]
                    logger.info(f"Found price for {ticker}: {price.iloc[0]:.4f}")
                else:
                    logger.warning(f"No data for {ticker} on {curve_date}")
                    fwd_data[month_code] = None
            except Exception as e:
                logger.warning(f"Error fetching {ticker}: {str(e)}")
                fwd_data[month_code] = None
        
        logger.info(f"Forward curve constructed with {len([v for v in fwd_data.values() if v is not None])} valid prices")
        return pd.DataFrame([fwd_data], index=[curve_date])
    
    def fetch_market_data(self, ticker: str, date: Optional[Union[str, date, datetime]] = None) -> Dict:
        """
        Fetch latest market data for a ticker from CSV
        
        Args:
            ticker: The ticker symbol
            date: The date for which to fetch market data (None for latest)
            
        Returns:
            Dict: A dictionary with market data (price, last_updated)
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
            
        try:
            # Try to get the latest price for the ticker
            end_date = pd.to_datetime(date)
            start_date = end_date - timedelta(days=7)  # Look back a week if needed
            
            price_series = self.fetch_data(ticker, start_date, end_date, verbose=False)
            if isinstance(price_series, pd.Series) and not price_series.empty:
                price = price_series.iloc[-1]
                last_updated = price_series.index[-1].strftime('%Y-%m-%d')
                
                return {
                    "price": float(price),
                    "lastUpdated": last_updated
                }
        except Exception as e:
            logger.error(f"Error fetching market data for {ticker}: {e}")
        
        # If we can't get real data, return a placeholder
        return {
            "price": 0.0,
            "lastUpdated": datetime.now().strftime('%Y-%m-%d')
        }
    
    def fetch_volatility_surface(self, primary_ticker: str, secondary_ticker: Optional[str] = None,
                               date: Optional[Union[str, date, datetime]] = None) -> Dict:
        """
        Fetch volatility surface data from CSV
        
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
        
        # Create a simple volatility smile for the primary index
        # We'll use a fixed pattern with higher vols at the extremes
        # In a real implementation, this would come from actual market data
        
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
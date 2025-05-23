// src/services/api.ts
import { PricingConfig, PricingResults } from '../components/Pricer';

// The base URL for the API - should be environment-specific
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api';

/**
 * Service class for interacting with the pricing API
 */
class PricingApiService {
  /**
   * Price an option based on the provided configuration
   * 
   * @param config The pricing configuration
   * @returns A promise resolving to the pricing results
   */
  async priceOption(config: PricingConfig): Promise<PricingResults> {
    try {
      const response = await fetch(`${API_BASE_URL}/pricing`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to price option');
      }

      return await response.json();
    } catch (error) {
      console.error('Error pricing option:', error);
      throw error;
    }
  }

  /**
   * Get market data for a specific index
   * 
   * @param index The index to get market data for
   * @param date The date for the market data (optional)
   * @returns A promise resolving to the market data
   */
  async getMarketData(index: string, date?: string): Promise<any> {
    try {
      const dateParam = date ? `&date=${date}` : '';
      const response = await fetch(`${API_BASE_URL}/market-data?index=${index}${dateParam}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to get market data');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting market data:', error);
      throw error;
    }
  }

  /**
   * Get forward curves for specified indices
   * 
   * @param indices Array of indices to fetch forward curves for
   * @param startDate Start date for the forward curve
   * @param endDate End date for the forward curve
   * @returns A promise resolving to the forward curves data
   */
  async getForwardCurves(indices: string[], startDate: string, endDate: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/forward-curves`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          indices,
          startDate,
          endDate,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to get forward curves');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting forward curves:', error);
      throw error;
    }
  }

  /**
   * Get volatility surface data for a specific index or spread
   * 
   * @param primaryIndex The primary index
   * @param secondaryIndex The secondary index (optional, for spread volatilities)
   * @returns A promise resolving to the volatility surface data
   */
  async getVolatilitySurface(primaryIndex: string, secondaryIndex?: string): Promise<any> {
    try {
      const secondaryParam = secondaryIndex ? `&secondary=${secondaryIndex}` : '';
      const response = await fetch(`${API_BASE_URL}/volatility-surface?primary=${primaryIndex}${secondaryParam}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to get volatility surface');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting volatility surface:', error);
      throw error;
    }
  }

  /**
   * Get available models for a specific option type
   * 
   * @param optionType The option type to get models for
   * @returns A promise resolving to the available models
   */
  async getAvailableModels(optionType: string): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/models?optionType=${optionType}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to get available models');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting available models:', error);
      throw error;
    }
  }
}

// Export a singleton instance of the service
export const pricingApi = new PricingApiService();
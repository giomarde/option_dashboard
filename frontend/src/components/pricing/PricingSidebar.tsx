// src/components/pricing/PricingSidebar.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';
import { getPhysicalDealById, getModelById } from '../../config/pricingConfig';

interface MarketDataType {
  primary: { 
    price: number; 
    lastUpdated: string;
  };
  secondary: { 
    price: number; 
    lastUpdated: string;
  };
}

interface PricingSidebarProps {
  config: PricingConfig;
  onQuote: () => void;
  isLoading: boolean;
  error: string | null;
  marketData?: MarketDataType;
}

const PricingSidebar: React.FC<PricingSidebarProps> = ({ 
  config, 
  onQuote, 
  isLoading, 
  error,
  marketData = { 
    primary: { price: 12.74, lastUpdated: new Date().toISOString() }, 
    secondary: { price: 12.45, lastUpdated: new Date().toISOString() } 
  }
}) => {
  const selectedDeal = getPhysicalDealById(config.deal_type);
  const selectedModel = getModelById(config.pricing_model);
  
  // Calculate option expiry date (delivery date - decision days prior)
  const calculateOptionExpiry = () => {
    try {
      const deliveryDate = new Date(config.evaluation_date);
      const expiryDate = new Date(deliveryDate);
      expiryDate.setDate(deliveryDate.getDate() - config.decision_days_prior);
      return expiryDate.toLocaleDateString();
    } catch (error) {
      return 'Invalid date';
    }
  };

  // Format the "last updated" time
  const formatLastUpdated = (dateString: string) => {
    try {
      const lastUpdated = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - lastUpdated.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins} min ago`;
      if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
      return `${Math.floor(diffMins / 1440)} days ago`;
    } catch (error) {
      return 'Unknown';
    }
  };

  // Calculate the current spread based on market data
  const calculateSpread = () => {
    return (marketData.primary.price - marketData.secondary.price).toFixed(2);
  };

  return (
    <div className="space-y-3 sticky top-4">
      {/* Quote Button */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <button
          onClick={onQuote}
          disabled={isLoading}
          className={`w-full py-3 px-4 font-semibold text-sm rounded-lg transition-all duration-200 ${
            isLoading
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
          }`}
        >
          {isLoading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></div>
              <span>Pricing...</span>
            </div>
          ) : (
            'Get Quote'
          )}
        </button>

        {error && (
          <div className="mt-3 p-2 bg-red-900 bg-opacity-30 border border-red-600 rounded-md text-red-200 text-xs">
            {error}
          </div>
        )}
      </div>

      {/* Configuration Summary */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h4 className="text-sm font-semibold text-white mb-3">Configuration Summary</h4>
        
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-400">Deal Type:</span>
            <span className="text-white font-medium">{selectedDeal?.name || 'Custom'}</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-400">Spread:</span>
            <span className="text-white font-medium">{config.primary_index}-{config.secondary_index}</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-400">Volume:</span>
            <span className="text-white font-medium">{(config.cargo_volume * config.num_options).toLocaleString()} MMBtu</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-400">Delivery Date:</span>
            <span className="text-white font-medium">
              {new Date(config.evaluation_date).toLocaleDateString()}
            </span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-400">Option Expiry:</span>
            <span className="text-white font-medium">{calculateOptionExpiry()}</span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-400">Strike:</span>
            <span className="text-blue-400 font-medium">
              {(config.secondary_differential - config.primary_differential + config.total_cost_per_option).toFixed(4)}
            </span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-400">Model:</span>
            <span className="text-white font-medium">{selectedModel?.name || 'Unknown'}</span>
          </div>
          
          {config.run_monte_carlo && (
            <div className="flex justify-between">
              <span className="text-gray-400">MC Paths:</span>
              <span className="text-white font-medium">{config.mc_paths.toLocaleString()}</span>
            </div>
          )}
        </div>
      </div>

      {/* Market Data Status */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h4 className="text-sm font-semibold text-white mb-3">Market Data</h4>
        
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">{config.primary_index}:</span>
            <div className="flex items-center space-x-1">
              <span className="text-white font-medium">${marketData.primary.price.toFixed(2)}</span>
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full"></span>
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-400">{config.secondary_index}:</span>
            <div className="flex items-center space-x-1">
              <span className="text-white font-medium">${marketData.secondary.price.toFixed(2)}</span>
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full"></span>
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Spread:</span>
            <span className="text-blue-400 font-medium">${calculateSpread()}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Vol:</span>
            <span className="text-white font-medium">37.06%</span>
          </div>
        </div>
        
        <div className="mt-3 pt-2 border-t border-gray-700">
          <div className="flex items-center space-x-1 text-xs text-gray-400">
            <span className="w-1.5 h-1.5 bg-green-400 rounded-full"></span>
            <span>
              Live • Updated {formatLastUpdated(marketData.primary.lastUpdated)}
            </span>
          </div>
        </div>
      </div>

      {/* Risk Disclaimer */}
      <div className="bg-gray-800 rounded-lg border border-yellow-600 p-3">
        <div className="flex items-start space-x-2">
          <span className="text-yellow-400 text-sm mt-0.5">⚠️</span>
          <div>
            <h5 className="text-yellow-400 font-semibold text-xs">Risk Disclaimer</h5>
            <p className="text-gray-300 text-xs mt-1 leading-relaxed">
              Option pricing subject to market volatility and model assumptions. Results are indicative only.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricingSidebar;
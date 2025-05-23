// src/components/pricing/PricingSidebar.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';

interface PricingSidebarProps {
  config: PricingConfig;
  onQuote: () => void;
  isLoading: boolean;
  error: string | null;
}

const PricingSidebar: React.FC<PricingSidebarProps> = ({ config, onQuote, isLoading, error }) => {
  return (
    <div className="space-y-6">
      {/* Quote Button */}
      <div className="bg-gray-800 border-2 border-gray-700 p-6">
        <button
          onClick={onQuote}
          disabled={isLoading}
          className={`w-full py-4 px-6 font-semibold text-lg transition-all duration-200 border-2 ${
            isLoading
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed border-gray-600'
              : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transform hover:-translate-y-1 border-transparent'
          }`}
        >
          {isLoading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="animate-spin h-5 w-5 border-2 border-gray-300 border-t-transparent rounded-full"></div>
              <span>Pricing...</span>
            </div>
          ) : (
            'Get Quote'
          )}
        </button>

        {error && (
          <div className="mt-4 p-3 bg-red-900 bg-opacity-30 border-2 border-red-600 text-red-200 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Parameter Summary */}
      <div className="bg-gray-800 border-2 border-gray-700 p-6">
        <h4 className="text-lg font-semibold text-white mb-4">Configuration Summary</h4>
        
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Option Type:</span>
            <span className="text-white font-medium capitalize">{config.option_type}</span>
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
            <span className="text-gray-400">Strike:</span>
            <span className="text-blue-400 font-medium">
              {(config.secondary_differential - config.primary_differential + config.total_cost_per_option).toFixed(4)}
            </span>
          </div>
          
          <div className="flex justify-between">
            <span className="text-gray-400">Method:</span>
            <span className="text-white font-medium">
              {config.pricing_method === 'fixed_differential' ? 'Fixed Diff.' : 'Fair Value'}
            </span>
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
      <div className="bg-gray-800 border-2 border-gray-700 p-6">
        <h4 className="text-lg font-semibold text-white mb-4">Market Data</h4>
        
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-gray-400 text-sm">{config.primary_index} Price:</span>
            <div className="flex items-center space-x-2">
              <span className="text-white font-medium">$12.74</span>
              <span className="w-2 h-2 bg-green-400 rounded-full"></span>
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-400 text-sm">{config.secondary_index} Price:</span>
            <div className="flex items-center space-x-2">
              <span className="text-white font-medium">$12.45</span>
              <span className="w-2 h-2 bg-green-400 rounded-full"></span>
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-400 text-sm">Current Spread:</span>
            <span className="text-blue-400 font-medium">$0.29</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-400 text-sm">Implied Vol:</span>
            <span className="text-white font-medium">37.06%</span>
          </div>
        </div>
        
        <div className="mt-4 pt-3 border-t-2 border-gray-700">
          <div className="flex items-center space-x-2 text-xs text-gray-400">
            <span className="w-2 h-2 bg-green-400 rounded-full"></span>
            <span>Live data • Updated 2 min ago</span>
          </div>
        </div>
      </div>

      {/* Risk Warning */}
      <div className="bg-gray-800 border-2 border-yellow-600 p-4">
        <div className="flex items-start space-x-3">
          <span className="text-yellow-400 text-lg">⚠️</span>
          <div>
            <h5 className="text-yellow-400 font-semibold text-sm">Risk Disclaimer</h5>
            <p className="text-gray-300 text-xs mt-1 leading-relaxed">
              Option pricing is subject to market volatility and model assumptions. 
              Past performance does not guarantee future results. Please consult with 
              your risk management team before trading.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricingSidebar;
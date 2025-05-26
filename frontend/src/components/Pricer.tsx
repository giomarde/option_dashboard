// src/components/Pricer.tsx
import React, { useState, useEffect } from 'react';
import PricingForm from './pricing/PricingForm';
import PricingResults from './pricing/PricingResults';
import PricingSidebar from './pricing/PricingSidebar';
import { getPhysicalDealById, getCompatibleModels } from '../config/pricingConfig';
import { pricingApi } from '../services/api';

export interface PricingConfig {
  // Deal Type
  deal_type: string;
  option_type: string;
  option_style: string;
  
  // Indices
  primary_index: string;
  secondary_index: string;
  output_unit: string;
  basket_indices: string[]; // For basket options (geographical arbitrage)
  
  // Contract Details
  cargo_volume: number;
  evaluation_date: string;
  num_options: number;
  first_delivery_month: string;
  first_delivery_year: number;
  delivery_day: number;
  decision_days_prior: number;
  contract_type: string; // 'single' or 'term'
  frequency: string; // 'weekly', 'biweekly', 'monthly', etc.
  pricing_date: string; // Date for fetching market data
  
  // Pricing
  pricing_model: string;
  pricing_method: string;
  total_cost_per_option: number;
  primary_differential: number;
  secondary_differential: number;
  locked_diff: string;
  
  // Monte Carlo
  run_monte_carlo: boolean;
  mc_paths: number;
  mc_seed: number;
  
  // Model specific parameters
  model_params: Record<string, any>;
}

export interface PricingResults {
  total_value: number;
  option_values: Record<string, number>;
  portfolio_greeks: {
    delta: number;
    gamma: number;
    vega: number;
    theta: number;
  };
  mc_results?: any;
  forward_spreads?: number[];
  volatilities?: number[];
}

const Pricer: React.FC = () => {
  const [config, setConfig] = useState<PricingConfig>({
    deal_type: 'regasification',
    option_type: 'vanilla_spread',
    option_style: 'european',
    primary_index: 'THE',
    secondary_index: 'TFU',
    output_unit: 'USD/MMBtu',
    cargo_volume: 3750000,
    evaluation_date: '2025-05-21',
    num_options: 1,
    first_delivery_month: 'Sep',
    first_delivery_year: 2025,
    delivery_day: 7,
    decision_days_prior: 21,
    pricing_model: 'bachelier',
    pricing_method: 'fixed_differential',
    pricing_date: new Date().toISOString().split('T')[0], // Date for fetching market data
    total_cost_per_option: 0.70,
    primary_differential: 0.0,
    secondary_differential: -0.55,
    locked_diff: 'no',
    run_monte_carlo: true,
    mc_paths: 10000,
    mc_seed: 42,
    contract_type: 'single',
    frequency: 'monthly',
    basket_indices: [],
    model_params: {}
  });

  const [results, setResults] = useState<PricingResults | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [marketData, setMarketData] = useState<{
    primary: { price: number; lastUpdated: string };
    secondary: { price: number; lastUpdated: string };
  }>({
    primary: { price: 0, lastUpdated: '' },
    secondary: { price: 0, lastUpdated: '' }
  });

  // Update option type when deal type changes
  useEffect(() => {
    const deal = getPhysicalDealById(config.deal_type);
    if (deal && deal.underlyingOptionType !== config.option_type) {
      const newConfig = {
        ...config,
        option_type: deal.underlyingOptionType
      };
      
      // Update pricing model if current one is not compatible
      const compatibleModels = getCompatibleModels(deal.underlyingOptionType);
      if (!compatibleModels.find(m => m.id === config.pricing_model)) {
        newConfig.pricing_model = compatibleModels[0]?.id || 'bachelier';
      }
      
      setConfig(newConfig);
    }
  }, [config.deal_type]);

  // Fetch market data when indices change
  useEffect(() => {
    const fetchMarketData = async () => {
      try {
        // Fetch primary index data
        const primaryData = await pricingApi.getMarketData(config.primary_index);
        // Fetch secondary index data
        const secondaryData = await pricingApi.getMarketData(config.secondary_index);
        
        setMarketData({
          primary: {
            price: primaryData.price,
            lastUpdated: primaryData.lastUpdated
          },
          secondary: {
            price: secondaryData.price,
            lastUpdated: secondaryData.lastUpdated
          }
        });
      } catch (err) {
        console.error("Failed to fetch market data:", err);
        // Fallback to demo data if API fails
        setMarketData({
          primary: { price: 12.74, lastUpdated: new Date().toISOString() },
          secondary: { price: 12.45, lastUpdated: new Date().toISOString() }
        });
      }
    };
    
    fetchMarketData();
  }, [config.primary_index, config.secondary_index]);

  const handleConfigChange = (field: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleQuote = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Call the API to price the option
      const pricingResults = await pricingApi.priceOption(config);
      setResults(pricingResults);
    } catch (err: any) {
      setError(err.message || 'Failed to price option. Please check your parameters and try again.');
      
      // If we're in development mode, use mock data for testing UI
      if (process.env.NODE_ENV === 'development') {
        console.warn('Using mock data for development');
        const mockResults: PricingResults = {
          total_value: 0.1957,
          option_values: {
            '2025-09-07': 0.195744
          },
          portfolio_greeks: {
            delta: 0.7381,
            gamma: 1.6307,
            vega: 0.1457,
            theta: -0.1120
          },
          forward_spreads: [0.290],
          volatilities: [0.3706],
          mc_results: {
            summary_statistics: {
              mean: 0.1957,
              std: 0.1559,
              percentiles: {
                5: 0.0096,
                25: 0.0684,
                50: 0.1603,
                75: 0.2927,
                95: 0.4959
              }
            },
            exercise_statistics: {
              exercise_probabilities: [{
                primary: 0.7381,
                secondary: 0.2619
              }]
            }
          }
        };
        setResults(mockResults);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full bg-gray-900 min-h-screen">
      <div className="px-6 py-4">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-white">Option Pricing Engine</h2>
          <p className="text-gray-400 text-sm">Configure and price sophisticated option structures</p>
        </div>

        <div className="grid grid-cols-12 gap-4">
          {/* Main Form Area */}
          <div className="col-span-9">
            <PricingForm 
              config={config} 
              onConfigChange={handleConfigChange}
            />
            
            {results && (
              <div className="mt-4">
                <PricingResults 
                  results={results} 
                  config={config}
                  onReprice={handleQuote} 
                />
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="col-span-3">
            <PricingSidebar 
              config={config}
              onQuote={handleQuote}
              isLoading={isLoading}
              error={error}
              marketData={marketData}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Pricer;
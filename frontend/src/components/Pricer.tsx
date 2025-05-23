// src/components/Pricer.tsx
import React, { useState } from 'react';
import PricingForm from './pricing/PricingForm';
import PricingResults from './pricing/PricingResults';
import PricingSidebar from './pricing/PricingSidebar';

export interface PricingConfig {
  option_type: string;
  option_style: string;
  primary_index: string;
  secondary_index: string;
  output_unit: string;
  cargo_volume: number;
  evaluation_date: string;
  num_options: number;
  first_delivery_month: string;
  first_delivery_year: number;
  delivery_day: number;
  decision_days_prior: number;
  pricing_method: string;
  total_cost_per_option: number;
  primary_differential: number;
  secondary_differential: number;
  locked_diff: string;
  run_monte_carlo: boolean;
  mc_paths: number;
  mc_seed: number;
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
    option_type: 'call',
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
    pricing_method: 'fixed_differential',
    total_cost_per_option: 0.70,
    primary_differential: 0.0,
    secondary_differential: -0.55,
    locked_diff: 'no',
    run_monte_carlo: true,
    mc_paths: 10000,
    mc_seed: 42,
  });

  const [results, setResults] = useState<PricingResults | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      // TODO: Replace with actual API call to your Python backend
      // const response = await fetch('/api/price-option', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(config)
      // });
      // const data = await response.json();
      
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Mock results based on your backend output
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
    } catch (err) {
      setError('Failed to price option. Please check your parameters and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full">
      <div className="px-8 py-6">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">Option Pricing Engine</h2>
          <p className="text-gray-400">Configure and price sophisticated option structures</p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
          {/* Main Form Area */}
          <div className="xl:col-span-3 space-y-6">
            <PricingForm 
              config={config} 
              onConfigChange={handleConfigChange}
            />
            
            {results && (
              <PricingResults results={results} config={config} />
            )}
          </div>

          {/* Sidebar */}
          <div className="xl:col-span-1">
            <PricingSidebar 
              config={config}
              onQuote={handleQuote}
              isLoading={isLoading}
              error={error}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Pricer;
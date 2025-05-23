// src/components/pricing/PricingResults.tsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { PricingConfig, PricingResults } from '../Pricer';

interface PricingResultsProps {
  results: PricingResults;
  config: PricingConfig;
}

const PricingResultsComponent: React.FC<PricingResultsProps> = ({ results, config }) => {
  const chartData = Object.entries(results.option_values).map(([date, value]) => {
    const strikePrice = config.secondary_differential - config.primary_differential + config.total_cost_per_option;
    const currentSpread = results.forward_spreads?.[0] || 0;
    const intrinsicValue = Math.max(0, currentSpread - strikePrice);
    
    return {
      date: new Date(date).toLocaleDateString(),
      value: value,
      intrinsic: intrinsicValue,
      time_value: Math.max(0, value - intrinsicValue)
    };
  });

  return (
    <div className="space-y-6">
      {/* Results Summary */}
      <div className="bg-gray-800 border-2 border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-6">Pricing Results</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <div className="text-center p-4 bg-gray-750 border-2 border-gray-600">
            <p className="text-2xl font-bold text-blue-400">
              {results.total_value.toFixed(6)}
            </p>
            <p className="text-gray-400 text-sm mt-1">Option Value ({config.output_unit})</p>
          </div>
          
          <div className="text-center p-4 bg-gray-750 border-2 border-gray-600">
            <p className="text-2xl font-bold text-green-400">
              ${(results.total_value * config.cargo_volume * config.num_options).toLocaleString()}
            </p>
            <p className="text-gray-400 text-sm mt-1">Total Contract Value</p>
          </div>
          
          <div className="text-center p-4 bg-gray-750 border-2 border-gray-600">
            <p className="text-2xl font-bold text-purple-400">
              {results.portfolio_greeks.delta.toFixed(4)}
            </p>
            <p className="text-gray-400 text-sm mt-1">Portfolio Delta</p>
          </div>
          
          <div className="text-center p-4 bg-gray-750 border-2 border-gray-600">
            <p className="text-2xl font-bold text-yellow-400">
              {((results.volatilities?.[0] ?? 0) * 100).toFixed(2)}%
            </p>
            <p className="text-gray-400 text-sm mt-1">Implied Volatility</p>
          </div>
        </div>

        {/* Greeks */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-md font-semibold text-white mb-3">Portfolio Greeks</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Delta:</span>
                <span className="text-white">{results.portfolio_greeks.delta.toFixed(6)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Gamma:</span>
                <span className="text-white">{results.portfolio_greeks.gamma.toFixed(6)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Vega:</span>
                <span className="text-white">{results.portfolio_greeks.vega.toFixed(6)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Theta:</span>
                <span className="text-white">{results.portfolio_greeks.theta.toFixed(6)}</span>
              </div>
            </div>
          </div>

          {results.mc_results && (
            <div>
              <h4 className="text-md font-semibold text-white mb-3">Monte Carlo Statistics</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Mean:</span>
                  <span className="text-white">{results.mc_results.summary_statistics.mean.toFixed(6)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Std Dev:</span>
                  <span className="text-white">{results.mc_results.summary_statistics.std.toFixed(6)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">95% VaR:</span>
                  <span className="text-white">{results.mc_results.summary_statistics.percentiles[5].toFixed(6)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Exercise Prob:</span>
                  <span className="text-white">
                    {(results.mc_results.exercise_statistics.exercise_probabilities[0].primary * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Charts */}
      <div className="bg-gray-800 border-2 border-gray-700 p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Option Value Breakdown</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: '2px solid #374151',
                  color: '#F9FAFB'
                }} 
              />
              <Legend />
              <Bar dataKey="intrinsic" stackId="a" fill="#10B981" name="Intrinsic Value" />
              <Bar dataKey="time_value" stackId="a" fill="#3B82F6" name="Time Value" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Hedging Recommendations */}
      {results.mc_results && (
        <div className="bg-gray-800 border-2 border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Hedging Recommendations</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-4 bg-gray-750 border-2 border-gray-600">
              <h4 className="text-sm font-semibold text-white mb-3">Recommended Position</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">{config.primary_index} Hedge:</span>
                  <span className="text-red-400 font-medium">
                    -{(results.portfolio_greeks.delta * config.cargo_volume).toLocaleString()} MMBtu
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">{config.secondary_index} Hedge:</span>
                  <span className="text-green-400 font-medium">
                    +{(results.portfolio_greeks.delta * config.cargo_volume).toLocaleString()} MMBtu
                  </span>
                </div>
              </div>
            </div>
            
            <div className="p-4 bg-gray-750 border-2 border-gray-600">
              <h4 className="text-sm font-semibold text-white mb-3">Exercise Probability</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Switch to {config.primary_index}:</span>
                  <span className="text-green-400 font-medium">
                    {(results.mc_results.exercise_statistics.exercise_probabilities[0].primary * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Stay with {config.secondary_index}:</span>
                  <span className="text-blue-400 font-medium">
                    {(results.mc_results.exercise_statistics.exercise_probabilities[0].secondary * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PricingResultsComponent;
// src/components/pricing/PricingResults.tsx
import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { PricingConfig, PricingResults as BasePricingResults } from '../Pricer';
import ModelParameters from './ModelParameters';

// Helper Type Definitions
export interface VolatilityPoint {
  strike: number;
  volatility: number;
  relative_strike?: number;
}

export interface VolatilitySmilesData {
  [key: string]: VolatilityPoint[];
}

export interface MonteCarloResults {
  summary_statistics: {
    mean: number;
    std: number;
    percentiles: {
      [key: number]: number;
    };
  };
  exercise_statistics: {
    exercise_probabilities: Array<{ primary: number; secondary: number }>;
  };
}

// Extend the BasePricingResults to include volatility data
export interface PricingResults extends BasePricingResults {
  volatility_smiles?: VolatilitySmilesData;
  mc_results?: MonteCarloResults;
  annualized_normal?: number;
  percentage_vol?: number;
}

interface PricingResultsProps {
  results: PricingResults;
  config: PricingConfig;
  onReprice?: (newConfig?: PricingConfig) => void;
}

const PricingResultsComponent: React.FC<PricingResultsProps> = ({ results, config, onReprice }) => {
  const [editableConfig, setEditableConfig] = useState<PricingConfig>(config);
  const [showVolInPercent, setShowVolInPercent] = useState(true);
  const [visibleSmiles, setVisibleSmiles] = useState({
    primary: false,
    secondary: false,
    spread: true,
  });

  useEffect(() => {
    setEditableConfig(config);
  }, [config]);

  // Set volatility in model params when results change
  useEffect(() => {
    if (results.annualized_normal !== undefined && editableConfig.model_params) {
      setEditableConfig(prevConfig => ({
        ...prevConfig,
        model_params: {
          ...prevConfig.model_params,
          volatility: results.annualized_normal
        }
      }));
    }
  }, [results.annualized_normal]);

  const handleModelParamsChange = (field: string, value: any) => {
    if (field === 'model_params') {
      setEditableConfig(prevConfig => ({
        ...prevConfig,
        model_params: value,
      }));
    }
  };

  const handleRepriceClick = () => {
    if (onReprice) {
      onReprice(editableConfig);
    } else {
      console.warn("Reprice action triggered, but no onReprice handler was provided.", editableConfig);
    }
  };

  const toggleSmileVisibility = (smileKey: keyof typeof visibleSmiles) => {
    setVisibleSmiles(prev => ({ ...prev, [smileKey]: !prev[smileKey] }));
  };

  // Format option values for the chart
  const optionValueChartData = Object.entries(results.option_values || {}).map(([date, value]) => {
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

  // Define colors for the different volatility lines
  const smileColors = {
    primary: '#3B82F6', // Blue for primary index vol
    secondary: '#10B981', // Green for secondary index vol
    spread: '#A78BFA',    // Purple for spread vol
  };

  // Extract volatility smile data from results or use mock data if needed
  const primaryIndex = config.primary_index || 'THE';
  const secondaryIndex = config.secondary_index || 'TFU';
  const spreadKey = `${primaryIndex}-${secondaryIndex}`;

  // Create mock data for testing if real data isn't available
  const mockVolatilityData = {
    primary: Array.from({ length: 45 }, (_, i) => {
      const baseStrike = 10.0;
      const strike = baseStrike * (0.7 + i * 0.02); // From 70% to 150% of base
      const relativeStrike = ((strike / baseStrike) - 1) * 100;
      const distFromCenter = Math.abs(strike - baseStrike);
      const vol = 0.3 + 0.15 * (distFromCenter / baseStrike) ** 2; // U-shaped smile
      return { strike, volatility: vol, relative_strike: relativeStrike };
    }),
    secondary: Array.from({ length: 45 }, (_, i) => {
      const baseStrike = 9.0;
      const strike = baseStrike * (0.7 + i * 0.02);
      const relativeStrike = ((strike / baseStrike) - 1) * 100;
      const distFromCenter = Math.abs(strike - baseStrike);
      const vol = 0.33 + 0.17 * (distFromCenter / baseStrike) ** 2;
      return { strike, volatility: vol, relative_strike: relativeStrike };
    }),
    spread: Array.from({ length: 45 }, (_, i) => {
      const baseStrike = 1.0;
      const range = 2.0; // From -1.0 to +1.0 around base
      const strike = baseStrike - range/2 + (range * i / 44);
      const relativeStrike = ((strike / baseStrike) - 1) * 100;
      const distFromCenter = Math.abs(strike - baseStrike);
      const vol = 0.35 + 0.2 * (distFromCenter / Math.max(0.5, Math.abs(baseStrike))) ** 2;
      return { strike, volatility: vol, relative_strike: relativeStrike };
    })
  };

  // Extract volatility smile data from results or use mock data
  const primarySmileData = results.volatility_smiles?.[primaryIndex] || mockVolatilityData.primary;
  const secondarySmileData = results.volatility_smiles?.[secondaryIndex] || mockVolatilityData.secondary;
  const spreadSmileData = results.volatility_smiles?.[spreadKey] || mockVolatilityData.spread;

  // Calculate appropriate domain for X axis based on visible data
  const calculateXDomain = () => {
    // Always use absolute strikes now, regardless of percentage mode
    const allStrikes = [
      ...(visibleSmiles.primary ? primarySmileData.map(p => p.strike) : []),
      ...(visibleSmiles.secondary ? secondarySmileData.map(p => p.strike) : []),
      ...(visibleSmiles.spread ? spreadSmileData.map(p => p.strike) : [])
    ];
    
    if (allStrikes.length === 0) return ['auto', 'auto'];
    
    // Calculate meaningful min/max by adding some padding
    const minStrike = Math.min(...allStrikes);
    const maxStrike = Math.max(...allStrikes);
    const range = maxStrike - minStrike;
    
    // Return domain with some padding on both sides
    return [minStrike - range * 0.05, maxStrike + range * 0.05];
  };

  // Calculate appropriate domain for Y axis based on visible data
  const calculateYDomain = () => {
    // Using percentage view for volatilities
    if (showVolInPercent) {
      const allVols = [
        ...(visibleSmiles.primary ? primarySmileData.map(p => p.volatility * 100) : []),
        ...(visibleSmiles.secondary ? secondarySmileData.map(p => p.volatility * 100) : []),
        ...(visibleSmiles.spread ? spreadSmileData.map(p => p.volatility * 100) : [])
      ];
      
      if (allVols.length === 0) return ['auto', 'auto'];
      return [Math.min(...allVols) * 0.9, Math.max(...allVols) * 1.1];
    } 
    // Using normal view for volatilities
    else {
      const allVols = [
        ...(visibleSmiles.primary ? primarySmileData.map(p => p.volatility) : []),
        ...(visibleSmiles.secondary ? secondarySmileData.map(p => p.volatility) : []),
        ...(visibleSmiles.spread ? spreadSmileData.map(p => p.volatility) : [])
      ];
      
      if (allVols.length === 0) return ['auto', 'auto'];
      return [Math.min(...allVols) * 0.9, Math.max(...allVols) * 1.1];
    }
  };

  // Calculate optimal bar size based on number of data points
  const getBarSize = (dataLength: number) => {
    if (dataLength <= 1) return 100;  // Narrow when only one bar
    if (dataLength <= 3) return 70;
    if (dataLength <= 6) return 40;
    return 30;  // Default for many bars
  };

  return (
    <div className="space-y-6 bg-gray-900 text-white">
      
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center mb-3">
          <h3 className="text-lg font-semibold text-white mb-2 sm:mb-0">Model Configuration</h3>
          <button
            onClick={handleRepriceClick}
            disabled={!onReprice}
            className="w-full sm:w-auto px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md disabled:bg-gray-500 disabled:cursor-not-allowed transition-colors duration-150"
          >
            Reprice
          </button>
        </div>
        <ModelParameters config={editableConfig} onConfigChange={handleModelParamsChange} />
      </div>

      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-base font-semibold text-white mb-4">Pricing Results</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <div className="text-center p-3 bg-gray-750 rounded-md border border-gray-600">
            <p className="text-xl font-bold text-blue-400">
              {results.total_value?.toFixed(4) ?? 'N/A'}
            </p>
            <p className="text-gray-400 text-xs mt-1">Option Value ({config.output_unit})</p>
          </div>
          <div className="text-center p-3 bg-gray-750 rounded-md border border-gray-600">
            <p className="text-xl font-bold text-green-400">
              ${(results.total_value * config.cargo_volume * config.num_options)?.toLocaleString() ?? 'N/A'}
            </p>
            <p className="text-gray-400 text-xs mt-1">Total Contract Value</p>
          </div>
          <div className="text-center p-3 bg-gray-750 rounded-md border border-gray-600">
            <p className="text-xl font-bold text-purple-400">
              {results.portfolio_greeks?.delta?.toFixed(4) ?? 'N/A'}
            </p>
            <p className="text-gray-400 text-xs mt-1">Portfolio Delta</p>
          </div>
          <div className="text-center p-3 bg-gray-750 rounded-md border border-gray-600">
            <p className="text-xl font-bold text-yellow-400">
              {results.percentage_vol?.toFixed(2)}%
            </p>
            <p className="text-gray-400 text-xs mt-1">Implied Volatility</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="text-sm font-semibold text-white mb-2">Portfolio Greeks</h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-gray-400">Delta:</span><span className="text-white">{results.portfolio_greeks?.delta?.toFixed(4) ?? 'N/A'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Gamma:</span><span className="text-white">{results.portfolio_greeks?.gamma?.toFixed(4) ?? 'N/A'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Vega:</span><span className="text-white">{results.portfolio_greeks?.vega?.toFixed(4) ?? 'N/A'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Theta:</span><span className="text-white">{results.portfolio_greeks?.theta?.toFixed(4) ?? 'N/A'}</span></div>
            </div>
          </div>
          {results.mc_results && (
          <div>
            <h4 className="text-sm font-semibold text-white mb-2">Monte Carlo Statistics</h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-gray-400">Mean:</span><span className="text-white">{results.mc_results.summary_statistics?.mean?.toFixed(4) ?? 'N/A'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Std Dev:</span><span className="text-white">{results.mc_results.summary_statistics?.std?.toFixed(4) ?? 'N/A'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">95% VaR:</span><span className="text-white">{results.mc_results.summary_statistics?.percentiles?.[5]?.toFixed(4) ?? 'N/A'}</span></div>
              <div className="flex justify-between">
                <span className="text-gray-400">Exercise Prob:</span>
                <span className="text-white">
                  {(results.mc_results.exercise_statistics?.exercise_probabilities?.[0]?.primary * 100)?.toFixed(1) ?? 'N/A'}%
                </span>
              </div>
            </div>
          </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Volatility Smiles Chart */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-base font-semibold text-white mb-1">Volatility Smiles</h3>
          
          {/* Display mode toggle at the top */}
          <div className="flex justify-between items-center mb-2 mt-1">
            <span className="text-xs text-gray-400">Display mode:</span>
            <div className="flex items-center bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setShowVolInPercent(false)}
                className={`px-3 py-1 text-xs rounded transition-colors duration-150 ${
                  !showVolInPercent ? 'bg-gray-600 text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Normal
              </button>
              <button
                onClick={() => setShowVolInPercent(true)}
                className={`px-3 py-1 text-xs rounded transition-colors duration-150 ${
                  showVolInPercent ? 'bg-gray-600 text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Percentage
              </button>
            </div>
          </div>
          
          <div className="h-64 md:h-80 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart margin={{ top: 15, right: 30, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="strike" 
                  stroke="#9CA3AF" 
                  tick={{ fontSize: 10 }} 
                  type="number" 
                  domain={calculateXDomain()}
                  label={{ 
                    value: "Strike", 
                    position: "insideBottom", 
                    dy: 15, 
                    fontSize: 10, 
                    fill: "#9CA3AF" 
                  }}
                  tickFormatter={(tick: number) => tick.toFixed(2)}
                />
                <YAxis 
                  stroke="#9CA3AF" 
                  tick={{ fontSize: 10 }} 
                  domain={calculateYDomain()}
                  tickFormatter={(tick: number) => showVolInPercent ? `${tick.toFixed(1)}%` : tick.toFixed(4)}
                  label={{ 
                    value: showVolInPercent ? "Volatility (%)" : "Annualized Normal Vol", 
                    angle: -90, 
                    position: 'insideLeft', 
                    dx: 10, 
                    fontSize: 10, 
                    fill: "#9CA3AF" 
                  }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '6px', color: '#F9FAFB', fontSize: '12px' }}
                  formatter={(value: any, name: string) => {
                    // Handle both direct value and function value cases
                    const actualValue = typeof value === 'function' ? value : value;
                    
                    if (name === 'volatility' || name.includes('Vol')) {
                      return showVolInPercent ? 
                        [`${(actualValue * 100).toFixed(2)}%`, 'Volatility'] : 
                        [actualValue.toFixed(4), 'Normal Vol'];
                    }
                    return [actualValue.toFixed(4), name];
                  }}
                  labelFormatter={(label: any) => {
                    return `Strike: ${typeof label === 'number' ? label.toFixed(4) : label}`;
                  }}
                />
                
                {visibleSmiles.primary && primarySmileData.length > 0 && (
                  <Line 
                    type="monotone" 
                    dataKey={showVolInPercent ? 
                      ((entry: VolatilityPoint) => entry.volatility * 100) : 
                      "volatility"
                    }
                    data={primarySmileData} 
                    stroke={smileColors.primary} 
                    name={`${primaryIndex} Vol`} 
                    dot={false} 
                    strokeWidth={2}
                    activeDot={{ r: 4 }}
                  />
                )}
                {visibleSmiles.secondary && secondarySmileData.length > 0 && (
                  <Line 
                    type="monotone" 
                    dataKey={showVolInPercent ? 
                      ((entry: VolatilityPoint) => entry.volatility * 100) : 
                      "volatility"
                    }
                    data={secondarySmileData} 
                    stroke={smileColors.secondary} 
                    name={`${secondaryIndex} Vol`} 
                    dot={false} 
                    strokeWidth={2}
                    activeDot={{ r: 4 }}
                  />
                )}
                {visibleSmiles.spread && spreadSmileData.length > 0 && (
                  <Line 
                    type="monotone" 
                    dataKey={showVolInPercent ? 
                      ((entry: VolatilityPoint) => entry.volatility * 100) : 
                      "volatility"
                    }
                    data={spreadSmileData} 
                    stroke={smileColors.spread} 
                    name="Spread Vol" 
                    dot={false} 
                    strokeWidth={2}
                    activeDot={{ r: 4 }}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
          
          {/* Move the smile selection buttons to the bottom */}
          <div className="flex justify-center flex-wrap gap-2 mt-3 text-xs">
            <button 
              onClick={() => toggleSmileVisibility('primary')} 
              className={`px-3 py-1 rounded transition-colors duration-150 ${visibleSmiles.primary ? 'bg-blue-600 text-white' : 'bg-gray-600 hover:bg-gray-500 text-gray-200'}`}
            >
              {primaryIndex} Vol
            </button>
            <button 
              onClick={() => toggleSmileVisibility('secondary')} 
              className={`px-3 py-1 rounded transition-colors duration-150 ${visibleSmiles.secondary ? 'bg-green-600 text-white' : 'bg-gray-600 hover:bg-gray-500 text-gray-200'}`}
            >
              {secondaryIndex} Vol
            </button>
            <button 
              onClick={() => toggleSmileVisibility('spread')} 
              className={`px-3 py-1 rounded transition-colors duration-150 ${visibleSmiles.spread ? 'bg-purple-500 text-white' : 'bg-gray-600 hover:bg-gray-500 text-gray-200'}`}
            >
              Spread Vol
            </button>
          </div>
        </div>

        {/* Option Value Breakdown Chart */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-base font-semibold text-white mb-3">Option Value Breakdown</h3>
          <div className="h-64 md:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={optionValueChartData} 
                margin={{ top: 0, right: 10, left: 10, bottom: 20 }}
                barSize={getBarSize(optionValueChartData.length)}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="date" 
                  stroke="#9CA3AF" 
                  tick={{ fontSize: 10 }} 
                  padding={{ left: optionValueChartData.length <= 1 ? 100 : 10, right: optionValueChartData.length <= 1 ? 100 : 10 }}
                />
                <YAxis 
                  stroke="#9CA3AF" 
                  tick={{ fontSize: 10 }} 
                  tickFormatter={(tick: number) => tick.toFixed(3)} 
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '6px', color: '#F9FAFB', fontSize: '12px' }}
                  formatter={(value: number) => value.toFixed(4)}
                />
                <Legend
                  layout="horizontal"
                  verticalAlign="bottom"
                  align="center"
                  wrapperStyle={{ paddingTop: 10, marginBottom: -10 }}
                />
                <Bar 
                  dataKey="intrinsic" 
                  stackId="a" 
                  fill="#10B981" 
                  name="Intrinsic Value" 
                />
                <Bar 
                  dataKey="time_value" 
                  stackId="a" 
                  fill="#3B82F6" 
                  name="Time Value"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {results.mc_results && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-base font-semibold text-white mb-3">Hedging Recommendations</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="p-3 bg-gray-750 rounded-md border border-gray-600">
              <h4 className="text-xs font-semibold text-white mb-2">Recommended Position</h4>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">{primaryIndex} Hedge:</span>
                  <span className="text-red-400 font-medium">
                    -{(results.portfolio_greeks?.delta * config.cargo_volume)?.toLocaleString() ?? 'N/A'} MMBtu
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">{secondaryIndex} Hedge:</span>
                  <span className="text-green-400 font-medium">
                    +{(results.portfolio_greeks?.delta * config.cargo_volume)?.toLocaleString() ?? 'N/A'} MMBtu
                  </span>
                </div>
              </div>
            </div>
            <div className="p-3 bg-gray-750 rounded-md border border-gray-600">
              <h4 className="text-xs font-semibold text-white mb-2">Exercise Probability</h4>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">Switch to {primaryIndex}:</span>
                  <span className="text-green-400 font-medium">
                    {(results.mc_results.exercise_statistics?.exercise_probabilities?.[0]?.primary * 100)?.toFixed(1) ?? 'N/A'}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Stay with {secondaryIndex}:</span>
                  <span className="text-blue-400 font-medium">
                    {(results.mc_results.exercise_statistics?.exercise_probabilities?.[0]?.secondary * 100)?.toFixed(1) ?? 'N/A'}%
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
// src/components/pricing/PricingResults.tsx
import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { PricingConfig, PricingResults as BasePricingResults } from '../Pricer';
import ModelParameters from './ModelParameters';

// Helper Type Definitions
export interface VolatilityPoint {
  strike: number;
  volatility: number;        // Normal volatility
  percentage_vol: number;    // Already calculated percentage volatility
  delta: number;             // Analytically calculated delta
  relative_strike: number;   // Percentage difference from forward price
  time_to_maturity?: number; // Time to maturity in years
  is_key_delta?: boolean;    // Flag for key delta points (0.25, 0.5, 0.75)
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
  market_context?: {
    evaluation_date: string;
    primary_price: number;
    secondary_price: number;
    forward_spreads: number[];
  };
}

interface PricingResultsProps {
  results: PricingResults;
  config: PricingConfig;
  onReprice?: (newConfig?: PricingConfig) => void;
}

const PricingResultsComponent: React.FC<PricingResultsProps> = ({ results, config, onReprice }) => {
  const [editableConfig, setEditableConfig] = useState<PricingConfig>(config);
  const [showVolInPercent, setShowVolInPercent] = useState(true);
  const [xAxisMode, setXAxisMode] = useState<'delta' | 'strike'>('delta');
  const [visibleSmiles, setVisibleSmiles] = useState({
    primary: false,
    secondary: false,
    spread: true,
  });
  const [maxChartValue, setMaxChartValue] = useState<number | undefined>(undefined);

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

  // Calculate max chart value to align both charts
  useEffect(() => {
    // Get max option value
    const optionValues = Object.values(results.option_values || {});
    const maxOptionValue = optionValues.length > 0 ? Math.max(...optionValues) : 0.2;
    
    // Get max volatility value (as a percentage)
    let maxVolPercentage = results.percentage_vol || 0;
    
    // Convert to decimal for comparison with option values
    maxVolPercentage = maxVolPercentage / 100;
    
    // Set the max value for both charts with some padding
    setMaxChartValue(Math.max(maxOptionValue * 1.2, maxVolPercentage * 1.2, 0.2));
  }, [results]);

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
    const intrinsicValue = (config.call_put || config.option_type) === 'call' 
      ? Math.max(0, currentSpread - strikePrice)
      : Math.max(0, strikePrice - currentSpread);
    
    return {
      date: new Date(date).toLocaleDateString(),
      value: value,
      intrinsic: intrinsicValue,
      time_value: Math.max(0, value - intrinsicValue)
    };
  });

  // Get current prices and key values for calculations
  const primaryPrice = results.market_context?.primary_price || 10.0;
  const secondaryPrice = results.market_context?.secondary_price || 9.0;
  const spreadPrice = results.market_context?.forward_spreads?.[0] || (primaryPrice - secondaryPrice);
  const strikePrice = config.secondary_differential - config.primary_differential + config.total_cost_per_option;

  // Define colors for the different volatility lines
  const smileColors = {
    primary: '#3B82F6', // Blue for primary index vol
    secondary: '#10B981', // Green for secondary index vol
    spread: '#A78BFA',    // Purple for spread vol
  };

  // Extract volatility smile data from results
  const primaryIndex = config.primary_index || 'THE';
  const secondaryIndex = config.secondary_index || 'TFU';
  const spreadKey = `${primaryIndex}-${secondaryIndex}`;

  // Extract volatility smile data or create fallback data if necessary
  const primarySmileData = results.volatility_smiles?.[primaryIndex] || [];
  const secondarySmileData = results.volatility_smiles?.[secondaryIndex] || [];
  const spreadSmileData = results.volatility_smiles?.[spreadKey] || [];

  // Calculate appropriate domain for X axis based on visible data and mode
  const calculateXDomain = () => {
    if (xAxisMode === 'delta') {
      // For delta, focus on the range [0.0, 1.0] for calls, [-1.0, 0.0] for puts
      // Since we're working with call options in most cases
      return [0.0, 1.0];
    } else {
      // For strike, calculate min/max from the data
      const allStrikes = [
        ...(visibleSmiles.primary ? primarySmileData.map(p => p.strike) : []),
        ...(visibleSmiles.secondary ? secondarySmileData.map(p => p.strike) : []),
        ...(visibleSmiles.spread ? spreadSmileData.map(p => p.strike) : [])
      ];
      
      if (allStrikes.length === 0) return ['auto', 'auto'];
      
      const minStrike = Math.min(...allStrikes);
      const maxStrike = Math.max(...allStrikes);
      const range = maxStrike - minStrike;
      
      return [minStrike - range * 0.05, maxStrike + range * 0.05];
    }
  };

  // Calculate appropriate domain for Y axis based on visible data
  const calculateYDomain = () => {
    if (showVolInPercent) {
      // For percentage volatility display
      const allVols = [
        ...(visibleSmiles.primary ? primarySmileData.map(p => p.percentage_vol) : []),
        ...(visibleSmiles.secondary ? secondarySmileData.map(p => p.percentage_vol) : []),
        ...(visibleSmiles.spread ? spreadSmileData.map(p => p.percentage_vol) : [])
      ];
      
      if (allVols.length === 0) return [0, 50]; // Default range for percentage display
      
      const minVol = Math.min(...allVols);
      const maxVol = Math.max(...allVols);
      const range = maxVol - minVol;
      
      return [0, maxVol + range * 0.1];
    } else {
      // For normal volatility display
      const allVols = [
        ...(visibleSmiles.primary ? primarySmileData.map(p => p.volatility) : []),
        ...(visibleSmiles.secondary ? secondarySmileData.map(p => p.volatility) : []),
        ...(visibleSmiles.spread ? spreadSmileData.map(p => p.volatility) : [])
      ];
      
      if (allVols.length === 0) return [0, 0.5]; // Default range for normal display
      
      const minVol = Math.min(...allVols);
      const maxVol = Math.max(...allVols);
      const range = maxVol - minVol;
      
      return [0, maxVol + range * 0.1];
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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-4">
          <div className="text-center p-2 bg-gray-750 rounded-md border border-gray-600">
            <p className="text-lg font-bold text-blue-400">
              {results.total_value?.toFixed(4) ?? 'N/A'}
            </p>
            <p className="text-gray-400 text-xs">Option Value ({config.output_unit})</p>
          </div>
          <div className="text-center p-2 bg-gray-750 rounded-md border border-gray-600">
            <p className="text-lg font-bold text-green-400">
              ${(results.total_value * config.cargo_volume * config.num_options)?.toLocaleString() ?? 'N/A'}
            </p>
            <p className="text-gray-400 text-xs">Total Contract Value</p>
          </div>
          <div className="text-center p-2 bg-gray-750 rounded-md border border-gray-600">
            <p className="text-lg font-bold text-purple-400">
              {results.portfolio_greeks?.delta?.toFixed(4) ?? 'N/A'}
            </p>
            <p className="text-gray-400 text-xs">Portfolio Delta</p>
          </div>
          <div className="text-center p-2 bg-gray-750 rounded-md border border-gray-600">
            <p className="text-lg font-bold text-yellow-400">
              {results.percentage_vol?.toFixed(2)}%
            </p>
            <p className="text-gray-400 text-xs">Implied Volatility</p>
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
          
          {/* Toggle controls for display mode and x-axis */}
          <div className="flex justify-center items-center mb-3 mt-1 space-x-4">
            <div className="flex items-center bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setXAxisMode('delta')}
                className={`px-4 py-1 text-xs rounded transition-colors duration-150 ${
                  xAxisMode === 'delta' ? 'bg-gray-600 text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Delta
              </button>
              <button
                onClick={() => setXAxisMode('strike')}
                className={`px-4 py-1 text-xs rounded transition-colors duration-150 ${
                  xAxisMode === 'strike' ? 'bg-gray-600 text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Strike
              </button>
            </div>
            
            <div className="flex items-center bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setShowVolInPercent(false)}
                className={`px-4 py-1 text-xs rounded transition-colors duration-150 ${
                  !showVolInPercent ? 'bg-gray-600 text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Normal
              </button>
              <button
                onClick={() => setShowVolInPercent(true)}
                className={`px-4 py-1 text-xs rounded transition-colors duration-150 ${
                  showVolInPercent ? 'bg-gray-600 text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Percentage
              </button>
            </div>
          </div>
          
          <div className="h-72 md:h-96 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart margin={{ top: 15, right: 30, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey={xAxisMode === 'delta' ? 'delta' : 'strike'} 
                  stroke="#9CA3AF" 
                  tick={{ fontSize: 10 }} 
                  type="number" 
                  domain={calculateXDomain()}
                  label={{ 
                    value: xAxisMode === 'delta' ? "Delta" : "Strike", 
                    position: "insideBottom", 
                    dy: 15, 
                    fontSize: 10, 
                    fill: "#9CA3AF" 
                  }}
                  tickFormatter={(tick) => typeof tick === 'number' ? tick.toFixed(2) : tick}
                />
                <YAxis 
                  stroke="#9CA3AF" 
                  tick={{ fontSize: 10 }} 
                  domain={calculateYDomain()}
                  tickFormatter={(tick) => showVolInPercent ? `${Number(tick).toFixed(1)}%` : Number(tick).toFixed(4)}
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
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151', 
                    borderRadius: '6px', 
                    color: '#F9FAFB', 
                    fontSize: '12px' 
                  }}
                  // Correct fix for the 'includes' error
                  formatter={(value, name) => {
                    // Format the tooltip display
                    const numValue = Number(value);
                    const nameStr = String(name); // Convert name to string
                    if (nameStr.includes('Vol')) { // Use nameStr, not name
                      if (showVolInPercent) {
                        return [`${numValue.toFixed(2)}%`, 'Volatility'];
                      } else {
                        return [numValue.toFixed(4), 'Normal Vol'];
                      }
                    }
                    return [numValue.toFixed(4), nameStr];
                  }}
                />
                
                {/* Reference lines for key deltas */}
                {xAxisMode === 'delta' && (
                  <>
                    <ReferenceLine x={0.25} stroke="#6B7280" strokeDasharray="3 3" />
                    <ReferenceLine x={0.5} stroke="#6B7280" strokeDasharray="3 3" />
                    <ReferenceLine x={0.75} stroke="#6B7280" strokeDasharray="3 3" />
                  </>
                )}
                
                {/* Reference lines for strike and forward price in strike mode */}
                {xAxisMode === 'strike' && (
                  <>
                    <ReferenceLine x={strikePrice} stroke="#EF4444" strokeDasharray="3 3" />
                    <ReferenceLine x={spreadPrice} stroke="#3B82F6" strokeDasharray="3 3" />
                  </>
                )}
                
                {/* Plot the volatility curves */}
                {visibleSmiles.primary && primarySmileData.length > 0 && (
                  <Line 
                    type="monotone" 
                    dataKey={showVolInPercent ? "percentage_vol" : "volatility"}
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
                    dataKey={showVolInPercent ? "percentage_vol" : "volatility"}
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
                    dataKey={showVolInPercent ? "percentage_vol" : "volatility"}
                    data={spreadSmileData} 
                    stroke={smileColors.spread} 
                    name="Spread Vol" 
                    dot={false} 
                    strokeWidth={2}
                    activeDot={{ r: 4 }}
                  />
                )}
                
                {/* Hide the standard Legend */}
                <Legend wrapperStyle={{ display: 'none' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          
          {/* Smile selection buttons */}
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
          <h3 className="text-base font-semibold text-white mb-3 flex justify-between">
            <span>Option Value Breakdown</span>
            <div className="text-xs text-gray-400 flex items-center space-x-2">
              <div className="flex items-center">
                <span className="inline-block w-3 h-3 bg-green-500 mr-1"></span>
                <span>Intrinsic Value</span>
              </div>
              <div className="flex items-center">
                <span className="inline-block w-3 h-3 bg-blue-500 mr-1"></span>
                <span>Time Value</span>
              </div>
            </div>
          </h3>
          <div className="h-72 md:h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={optionValueChartData} 
                margin={{ top: 5, right: 30, left: 20, bottom: 30 }}
                barSize={getBarSize(optionValueChartData.length)}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="date" 
                  stroke="#9CA3AF" 
                  tick={{ fontSize: 10 }} 
                />
                <YAxis 
                  stroke="#9CA3AF" 
                  tick={{ fontSize: 10 }} 
                  tickFormatter={(tick) => Number(tick).toFixed(3)} 
                  // If we have maxChartValue, use it to align with volatility chart 
                  domain={[0, maxChartValue ? () => maxChartValue : (dataMax: number) => Math.max(dataMax * 1.1, 0.1)]}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '6px', color: '#F9FAFB', fontSize: '12px' }}
                  formatter={(value) => Number(value).toFixed(4)}
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
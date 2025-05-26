// src/components/pricing/PricingResults.tsx
import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { PricingConfig, PricingResults as BasePricingResults } from '../Pricer';
import ModelParameters from './ModelParameters';

// Helper Type Definitions
export interface VolatilityPoint {
  strike: number;
  volatility: number;
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
}

interface PricingResultsProps {
  results: PricingResults;
  config: PricingConfig;
  onReprice?: (newConfig?: PricingConfig) => void;
}

const PricingResultsComponent: React.FC<PricingResultsProps> = ({ results, config, onReprice }) => {
  const [editableConfig, setEditableConfig] = useState<PricingConfig>(config);
  const [showVolInPercent, setShowVolInPercent] = useState(true);

  useEffect(() => {
    setEditableConfig(config);
  }, [config]);

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

  // Volatility smile toggle state
  const [visibleSmiles, setVisibleSmiles] = useState({
    primary: true,
    secondary: true,
    spread: true,
  });

  const toggleSmileVisibility = (smileKey: keyof typeof visibleSmiles) => {
    setVisibleSmiles(prev => ({ ...prev, [smileKey]: !prev[smileKey] }));
  };

  // Define colors for the different volatility lines
  const smileColors = {
    primary: '#3B82F6', // Blue for primary index vol
    secondary: '#10B981', // Green for secondary index vol
    spread: '#A78BFA',    // Purple for spread vol
  };

  // Create mock data if real data isn't available
  const mockVolatilityData = {
    primary: [
      { strike: 9.5, volatility: 0.34 }, { strike: 9.75, volatility: 0.32 },
      { strike: 10.0, volatility: 0.30 }, { strike: 10.25, volatility: 0.32 },
      { strike: 10.5, volatility: 0.35 }
    ],
    secondary: [
      { strike: 8.5, volatility: 0.37 }, { strike: 8.75, volatility: 0.34 },
      { strike: 9.0, volatility: 0.33 }, { strike: 9.25, volatility: 0.35 },
      { strike: 9.5, volatility: 0.38 }
    ],
    spread: [
      { strike: 0.5, volatility: 0.48 }, { strike: 0.75, volatility: 0.46 },
      { strike: 1.0, volatility: 0.45 }, { strike: 1.25, volatility: 0.47 },
      { strike: 1.5, volatility: 0.50 }
    ]
  };

  // Extract volatility smile data from results or use mock data
  const primaryIndex = config.primary_index || 'THE';
  const secondaryIndex = config.secondary_index || 'TFU';
  const spreadKey = `${primaryIndex}-${secondaryIndex}`;

  const primarySmileData = results.volatility_smiles?.[primaryIndex] || mockVolatilityData.primary;
  const secondarySmileData = results.volatility_smiles?.[secondaryIndex] || mockVolatilityData.secondary;
  const spreadSmileData = results.volatility_smiles?.[spreadKey] || mockVolatilityData.spread;

  // Calculate chart domains based on visible data
  const calculateXDomain = () => {
    const allStrikes = [
      ...(visibleSmiles.primary ? primarySmileData.map(p => p.strike) : []),
      ...(visibleSmiles.secondary ? secondarySmileData.map(p => p.strike) : []),
      ...(visibleSmiles.spread ? spreadSmileData.map(p => p.strike) : [])
    ];
    
    if (allStrikes.length === 0) return ['auto', 'auto'] as [number, number] | ['auto', 'auto'];
    return [Math.min(...allStrikes) * 0.95, Math.max(...allStrikes) * 1.05] as [number, number];
  };

  const calculateYDomain = () => {
    const allVols = [
      ...(visibleSmiles.primary ? primarySmileData.map(p => p.volatility) : []),
      ...(visibleSmiles.secondary ? secondarySmileData.map(p => p.volatility) : []),
      ...(visibleSmiles.spread ? spreadSmileData.map(p => p.volatility) : [])
    ];
    
    if (allVols.length === 0) return ['auto', 'auto'] as [number, number] | ['auto', 'auto'];
    return [Math.min(...allVols) * 0.9, Math.max(...allVols) * 1.1] as [number, number];
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
                    {results.total_value?.toFixed(6) ?? 'N/A'}
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
                    {((results.volatilities?.[0] ?? 0) * 100).toFixed(2)}%
                </p>
                <p className="text-gray-400 text-xs mt-1">Implied Volatility</p>
            </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
                <h4 className="text-sm font-semibold text-white mb-2">Portfolio Greeks</h4>
                <div className="space-y-1 text-xs">
                    <div className="flex justify-between"><span className="text-gray-400">Delta:</span><span className="text-white">{results.portfolio_greeks?.delta?.toFixed(6) ?? 'N/A'}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Gamma:</span><span className="text-white">{results.portfolio_greeks?.gamma?.toFixed(6) ?? 'N/A'}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Vega:</span><span className="text-white">{results.portfolio_greeks?.vega?.toFixed(6) ?? 'N/A'}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Theta:</span><span className="text-white">{results.portfolio_greeks?.theta?.toFixed(6) ?? 'N/A'}</span></div>
                </div>
            </div>
            {results.mc_results && (
            <div>
                <h4 className="text-sm font-semibold text-white mb-2">Monte Carlo Statistics</h4>
                <div className="space-y-1 text-xs">
                    <div className="flex justify-between"><span className="text-gray-400">Mean:</span><span className="text-white">{results.mc_results.summary_statistics?.mean?.toFixed(6) ?? 'N/A'}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Std Dev:</span><span className="text-white">{results.mc_results.summary_statistics?.std?.toFixed(6) ?? 'N/A'}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">95% VaR:</span><span className="text-white">{results.mc_results.summary_statistics?.percentiles?.[5]?.toFixed(6) ?? 'N/A'}</span></div>
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
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-base font-semibold text-white mb-1">Volatility Smiles</h3>
          
          {/* Move the smile selection buttons to the top */}
          <div className="flex justify-center flex-wrap gap-2 mb-3 text-xs">
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
          
          {/* Display mode toggle */}
          <div className="flex justify-center items-center mb-2 mt-1">
            <span className="text-xs text-gray-400 mr-2">Display as:</span>
            <div className="flex items-center bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setShowVolInPercent(false)}
                className={`px-3 py-1 text-xs rounded transition-colors duration-150 ${
                  !showVolInPercent ? 'bg-gray-600 text-white' : 'text-gray-300 hover:text-white'
                }`}
              >
                Decimal
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
                    label={{ value: "Strike", position: "insideBottom", dy:15, fontSize: 10, fill:"#9CA3AF" }}
                />
                <YAxis 
                    stroke="#9CA3AF" 
                    tick={{ fontSize: 10 }} 
                    domain={calculateYDomain()}
                    tickFormatter={(tick: number) => showVolInPercent ? `${(tick * 100).toFixed(0)}%` : tick.toFixed(3)}
                    label={{ value: "Volatility", angle: -90, position: 'insideLeft', dx:10, fontSize: 10, fill:"#9CA3AF" }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '6px', color: '#F9FAFB', fontSize: '12px' }}
                  formatter={(value: number, name: string) => showVolInPercent ? [`${(value * 100).toFixed(2)}%`, name] : [value.toFixed(4), name]}
                />
                
                {visibleSmiles.primary && primarySmileData.length > 0 && (
                  <Line 
                    type="monotone" 
                    dataKey="volatility" 
                    data={primarySmileData} 
                    stroke={smileColors.primary} 
                    name={`${primaryIndex} Vol`} 
                    dot={false} 
                    strokeWidth={2}
                  />
                )}
                {visibleSmiles.secondary && secondarySmileData.length > 0 && (
                  <Line 
                    type="monotone" 
                    dataKey="volatility" 
                    data={secondarySmileData} 
                    stroke={smileColors.secondary} 
                    name={`${secondaryIndex} Vol`} 
                    dot={false} 
                    strokeWidth={2}
                  />
                )}
                {visibleSmiles.spread && spreadSmileData.length > 0 && (
                  <Line 
                    type="monotone" 
                    dataKey="volatility" 
                    data={spreadSmileData} 
                    stroke={smileColors.spread} 
                    name="Spread Vol" 
                    dot={false} 
                    strokeWidth={2}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-base font-semibold text-white mb-3">Option Value Breakdown</h3>
          <div className="h-64 md:h-80 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={optionValueChartData} 
                margin={{ top: 15, right: 20, left: 0, bottom: 5 }}
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
                  formatter={(value: number) => value.toFixed(6)}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                <Bar 
                  dataKey="intrinsic" 
                  stackId="a" 
                  fill="#10B981" 
                  name="Intrinsic Value" 
                  radius={optionValueChartData.length <= 1 ? [8, 8, 0, 0] : [0, 0, 0, 0]}
                />
                <Bar 
                  dataKey="time_value" 
                  stackId="a" 
                  fill="#3B82F6" 
                  name="Time Value"
                  radius={optionValueChartData.length <= 1 ? [0, 0, 8, 8] : [0, 0, 0, 0]} 
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
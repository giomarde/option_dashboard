// src/components/pricing/PricingResults.tsx
import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
// Assuming PricingConfig and the base PricingResults are correctly defined in '../Pricer'
import { PricingConfig, PricingResults as BasePricingResults } from '../Pricer';
import ModelParameters from './ModelParameters';

// --- Helper Type Definitions ---
// Ideally, these should be defined in and exported from '../Pricer.ts' or a central types file.
export interface VolatilityPoint {
  strike: number;
  volatility: number;
}

export interface VolatilitySmilesData {
  primary?: VolatilityPoint[];
  secondary?: VolatilityPoint[];
  spread?: VolatilityPoint[];
}

export interface MonteCarloResults {
  summary_statistics: {
    mean: number;
    std: number;
    percentiles: number[];
  };
  exercise_statistics: {
    exercise_probabilities: Array<{ primary: number; secondary: number }>;
  };
}

// Extend the BasePricingResults to include the new fields if not already present
export interface PricingResults extends BasePricingResults {
  volatility_smiles?: VolatilitySmilesData;
  mc_results?: MonteCarloResults; // Ensure mc_results uses the correct type
}
// --- End Helper Type Definitions ---

interface PricingResultsProps {
  results: PricingResults;
  config: PricingConfig;
  onReprice?: (newConfig: PricingConfig) => void;
}

const PricingResultsComponent: React.FC<PricingResultsProps> = ({ results, config, onReprice }) => {
  const [editableConfig, setEditableConfig] = useState<PricingConfig>(config);

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

  const [visibleSmiles, setVisibleSmiles] = useState({
    primary: true,
    secondary: true,
    spread: true,
  });

  const toggleSmileVisibility = (smileKey: keyof typeof visibleSmiles) => {
    setVisibleSmiles(prev => ({ ...prev, [smileKey]: !prev[smileKey] }));
  };

  const smileColors = {
    primary: '#3B82F6', // Blue for THE Vol
    secondary: '#10B981', // Green for TFU Vol
    spread: '#A78BFA',    // Purple for Spread Vol (adjusted for better visibility)
  };

  // --- Mock Data for Volatility Smiles (used if results.volatility_smiles is empty) ---
  const mockPrimarySmile: VolatilityPoint[] = [
    { strike: 80, volatility: 0.35 }, { strike: 90, volatility: 0.32 },
    { strike: 100, volatility: 0.30 }, { strike: 110, volatility: 0.33 },
    { strike: 120, volatility: 0.36 },
  ];
  const mockSecondarySmile: VolatilityPoint[] = [
    { strike: 85, volatility: 0.38 }, { strike: 95, volatility: 0.34 },
    { strike: 105, volatility: 0.32 }, { strike: 115, volatility: 0.35 },
    { strike: 125, volatility: 0.39 },
  ];
  const mockSpreadSmile: VolatilityPoint[] = [
    { strike: -10, volatility: 0.50 }, { strike: -5, volatility: 0.47 },
    { strike: 0, volatility: 0.45 }, { strike: 5, volatility: 0.48 },
    { strike: 10, volatility: 0.52 },
  ];
  // --- End Mock Data ---

  const primarySmileData = results.volatility_smiles?.primary && results.volatility_smiles.primary.length > 0 ? results.volatility_smiles.primary : mockPrimarySmile;
  const secondarySmileData = results.volatility_smiles?.secondary && results.volatility_smiles.secondary.length > 0 ? results.volatility_smiles.secondary : mockSecondarySmile;
  const spreadSmileData = results.volatility_smiles?.spread && results.volatility_smiles.spread.length > 0 ? results.volatility_smiles.spread : mockSpreadSmile;

  const allStrikes = [
    ...primarySmileData.map((p: VolatilityPoint) => p.strike),
    ...secondarySmileData.map((p: VolatilityPoint) => p.strike),
    ...spreadSmileData.map((p: VolatilityPoint) => p.strike),
  ];
  const xDomainSmiles: [number, number] | ['auto', 'auto'] = allStrikes.length > 0 
    ? [Math.min(...allStrikes), Math.max(...allStrikes)] 
    : ['auto', 'auto'];

  const allVols = [
    ...primarySmileData.map((p: VolatilityPoint) => p.volatility),
    ...secondarySmileData.map((p: VolatilityPoint) => p.volatility),
    ...spreadSmileData.map((p: VolatilityPoint) => p.volatility),
  ];
  const yDomainSmiles: [number, number] | ['auto', 'auto'] = allVols.length > 0 
    ? [Math.min(0, ...allVols) * 0.9, Math.max(...allVols) * 1.1] 
    : ['auto', 'auto'];

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
          <div className="flex justify-center flex-wrap gap-2 mb-3 text-xs">
            <button 
                onClick={() => toggleSmileVisibility('primary')} 
                className={`px-3 py-1 rounded transition-colors duration-150 ${visibleSmiles.primary ? 'bg-blue-600 text-white' : 'bg-gray-600 hover:bg-gray-500 text-gray-200'}`}
            >
              {config.primary_index || 'THE'} Vol
            </button>
            <button 
                onClick={() => toggleSmileVisibility('secondary')} 
                className={`px-3 py-1 rounded transition-colors duration-150 ${visibleSmiles.secondary ? 'bg-green-600 text-white' : 'bg-gray-600 hover:bg-gray-500 text-gray-200'}`}
            >
              {config.secondary_index || 'TFU'} Vol
            </button>
            <button 
                onClick={() => toggleSmileVisibility('spread')} 
                className={`px-3 py-1 rounded transition-colors duration-150 ${visibleSmiles.spread ? 'bg-purple-500 text-white' : 'bg-gray-600 hover:bg-gray-500 text-gray-200'}`}
            >
              Spread Vol
            </button>
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
                    domain={xDomainSmiles}
                    label={{ value: "Strike", position: "insideBottom", dy:15, fontSize: 10, fill:"#9CA3AF" }}
                />
                <YAxis 
                    stroke="#9CA3AF" 
                    tick={{ fontSize: 10 }} 
                    domain={yDomainSmiles}
                    tickFormatter={(tick: number) => `${(tick * 100).toFixed(0)}%`}
                    label={{ value: "Volatility", angle: -90, position: 'insideLeft', dx:10, fontSize: 10, fill:"#9CA3AF" }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '6px', color: '#F9FAFB', fontSize: '12px' }}
                  formatter={(value: number, name: string) => [`${(value * 100).toFixed(2)}%`, name]}
                />
                {visibleSmiles.primary && primarySmileData.length > 0 && (
                  <Line type="monotone" dataKey="volatility" data={primarySmileData} stroke={smileColors.primary} name={`${config.primary_index || 'THE'} Vol`} dot={false} strokeWidth={2}/>
                )}
                {visibleSmiles.secondary && secondarySmileData.length > 0 && (
                  <Line type="monotone" dataKey="volatility" data={secondarySmileData} stroke={smileColors.secondary} name={`${config.secondary_index || 'TFU'} Vol`} dot={false} strokeWidth={2}/>
                )}
                {visibleSmiles.spread && spreadSmileData.length > 0 && (
                  <Line type="monotone" dataKey="volatility" data={spreadSmileData} stroke={smileColors.spread} name="Spread Vol" dot={false} strokeWidth={2}/>
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h3 className="text-base font-semibold text-white mb-3">Option Value Breakdown</h3>
          <div className="h-64 md:h-80 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={optionValueChartData} margin={{ top: 15, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#9CA3AF" tick={{ fontSize: 10 }} />
                <YAxis stroke="#9CA3AF" tick={{ fontSize: 10 }} tickFormatter={(tick: number) => tick.toFixed(3)} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: '6px', color: '#F9FAFB', fontSize: '12px' }}
                  formatter={(value: number) => value.toFixed(6)}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                <Bar dataKey="intrinsic" stackId="a" fill="#10B981" name="Intrinsic Value" />
                <Bar dataKey="time_value" stackId="a" fill="#3B82F6" name="Time Value" />
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
                        <span className="text-gray-400">{config.primary_index} Hedge:</span>
                        <span className="text-red-400 font-medium">
                            -{(results.portfolio_greeks?.delta * config.cargo_volume)?.toLocaleString() ?? 'N/A'} MMBtu
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">{config.secondary_index} Hedge:</span>
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
                        <span className="text-gray-400">Switch to {config.primary_index}:</span>
                        <span className="text-green-400 font-medium">
                            {(results.mc_results.exercise_statistics?.exercise_probabilities?.[0]?.primary * 100)?.toFixed(1) ?? 'N/A'}%
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-400">Stay with {config.secondary_index}:</span>
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
// src/components/pricing/PricingParameters.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';
import FormField from '../common/FormField';

interface PricingParametersProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const PricingParameters: React.FC<PricingParametersProps> = ({ config, onConfigChange }) => {
  return (
    <div className="bg-gray-800 border-2 border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-white mb-6 pb-3 border-b-2 border-gray-700">
        Pricing Parameters
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FormField
          label="Pricing Method"
          type="select"
          value={config.pricing_method}
          onChange={(value) => onConfigChange('pricing_method', value)}
          options={[
            { value: 'fixed_differential', label: 'Fixed Differential' },
            { value: 'fair_value', label: 'Fair Value' }
          ]}
        />

        <FormField
          label="Regas Cost (USD/MMBtu)"
          type="number"
          value={config.total_cost_per_option}
          onChange={(value) => onConfigChange('total_cost_per_option', Number(value))}
          step={0.01}
          min={0}
          helperText="Total regasification cost per MMBtu"
        />

        <FormField
          label="Lock Differential"
          type="select"
          value={config.locked_diff}
          onChange={(value) => onConfigChange('locked_diff', value)}
          options={[
            { value: 'no', label: 'No' },
            { value: 'yes', label: 'Yes' }
          ]}
          helperText="Whether differential is locked"
        />

        <FormField
          label="Primary Differential"
          type="number"
          value={config.primary_differential}
          onChange={(value) => onConfigChange('primary_differential', Number(value))}
          step={0.01}
          disabled={config.pricing_method === 'fair_value'}
          helperText={`${config.primary_index} differential`}
        />

        <FormField
          label="Secondary Differential"
          type="number"
          value={config.secondary_differential}
          onChange={(value) => onConfigChange('secondary_differential', Number(value))}
          step={0.01}
          disabled={config.pricing_method === 'fair_value'}
          helperText={`${config.secondary_index} differential`}
        />
      </div>

      {/* Strike Price Calculation */}
      <div className="mt-6 p-4 bg-gray-750 border-2 border-gray-600">
        <h4 className="text-sm font-semibold text-white mb-3">Strike Price Calculation</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-400">Secondary Differential:</span>
              <span className="text-white">{config.secondary_differential.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Primary Differential:</span>
              <span className="text-white">{config.primary_differential.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Regas Cost:</span>
              <span className="text-white">{config.total_cost_per_option.toFixed(4)}</span>
            </div>
            <div className="flex justify-between border-t-2 border-gray-600 pt-2">
              <span className="text-gray-300 font-medium">Strike Price (K):</span>
              <span className="text-blue-400 font-semibold">
                {(config.secondary_differential - config.primary_differential + config.total_cost_per_option).toFixed(4)}
              </span>
            </div>
          </div>
          <div className="text-xs text-gray-400 space-y-1">
            <p>• Strike = Secondary Diff - Primary Diff + Regas Cost</p>
            <p>• For call options: exercise when spread > strike</p>
            <p>• For put options: exercise when spread &lt; strike</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricingParameters;
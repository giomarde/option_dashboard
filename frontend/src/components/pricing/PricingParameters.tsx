// src/components/pricing/PricingParameters.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';
import FormField from '../common/FormField';
import { PRICING_MODELS, OPTION_TYPES, getCompatibleModels } from '../../config/pricingConfig';

interface PricingParametersProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const PricingParameters: React.FC<PricingParametersProps> = ({ config, onConfigChange }) => {
  const compatibleModels = getCompatibleModels(config.option_type);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-base font-semibold text-white mb-3">Pricing Parameters</h3>
      
      <div className="grid grid-cols-6 gap-3">
        {/* Option Type/Style Controls - Moved from Contract Specifications */}
        <FormField
          label="Option Type"
          type="select"
          value={config.option_type}
          onChange={(value) => onConfigChange('option_type', value)}
          options={OPTION_TYPES.map(t => ({ value: t.id, label: t.name }))}
          size="sm"
        />
        
        <FormField
          label="Option Style"
          type="select"
          value={config.option_style}
          onChange={(value) => onConfigChange('option_style', value)}
          options={[
            { value: 'european', label: 'European' },
            { value: 'american', label: 'American' }
          ]}
          size="sm"
        />
        
        <FormField
          label="Pricing Model"
          type="select"
          value={config.pricing_model}
          onChange={(value) => onConfigChange('pricing_model', value)}
          options={compatibleModels.map(m => ({ 
            value: m.id, 
            label: m.name 
          }))}
          size="sm"
          helperText={compatibleModels.find(m => m.id === config.pricing_model)?.description}
        />

        <FormField
          label="Method"
          type="select"
          value={config.pricing_method}
          onChange={(value) => onConfigChange('pricing_method', value)}
          options={[
            { value: 'fixed_differential', label: 'Fixed Differential' },
            { value: 'fair_value', label: 'Fair Value' }
          ]}
          size="sm"
        />

        <FormField
          label="Exercise Cost"
          type="number"
          value={config.total_cost_per_option}
          onChange={(value) => onConfigChange('total_cost_per_option', Number(value))}
          step={0.01}
          min={0}
          size="sm"
        />

        <FormField
          label="Locked Differential"
          type="select"
          value={config.locked_diff}
          onChange={(value) => onConfigChange('locked_diff', value)}
          options={[
            { value: 'no', label: 'No' },
            { value: 'yes', label: 'Yes' }
          ]}
          size="sm"
        />

        <FormField
          label="Primary Differential"
          type="number"
          value={config.primary_differential}
          onChange={(value) => onConfigChange('primary_differential', Number(value))}
          step={0.01}
          disabled={config.pricing_method === 'fair_value'}
          size="sm"
        />

        <FormField
          label="Secondary Differential"
          type="number"
          value={config.secondary_differential}
          onChange={(value) => onConfigChange('secondary_differential', Number(value))}
          step={0.01}
          disabled={config.pricing_method === 'fair_value'}
          size="sm"
        />
      </div>

      {/* Strike Price Calculation */}
      <div className="mt-3 p-2 bg-gray-750 rounded-md">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-4">
            <span className="text-gray-400">Strike = {config.secondary_differential.toFixed(2)} - {config.primary_differential.toFixed(2)} + {config.total_cost_per_option.toFixed(2)}</span>
            <span className="text-gray-300">=</span>
            <span className="text-blue-400 font-semibold">
              {(config.secondary_differential - config.primary_differential + config.total_cost_per_option).toFixed(4)}
            </span>
          </div>
          <span className="text-gray-400">
            Exercise when spread {config.option_type === 'call' ? '>' : '<'} strike
          </span>
        </div>
      </div>
    </div>
  );
};

export default PricingParameters;
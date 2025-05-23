// src/components/pricing/ModelParameters.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';
import FormField from '../common/FormField';
import { getModelById } from '../../config/pricingConfig';

interface ModelParametersProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const ModelParameters: React.FC<ModelParametersProps> = ({ config, onConfigChange }) => {
  const selectedModel = getModelById(config.pricing_model);
  
  if (!selectedModel || selectedModel.parameters.length === 0) {
    return null;
  }

  const handleModelParamChange = (paramId: string, value: any) => {
    onConfigChange('model_params', {
      ...config.model_params,
      [paramId]: value
    });
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-base font-semibold text-white mb-3">
        {selectedModel.name} Model Parameters
      </h3>
      
      <div className="grid grid-cols-6 gap-3">
        {selectedModel.parameters.map((param) => (
          <FormField
            key={param.id}
            label={param.name}
            type={param.type}
            value={config.model_params[param.id] ?? param.defaultValue}
            onChange={(value) => handleModelParamChange(param.id, value)}
            min={param.min}
            max={param.max}
            step={param.step}
            options={param.options}
            helperText={param.helperText}
            size="sm"
          />
        ))}
      </div>
    </div>
  );
};

export default ModelParameters;
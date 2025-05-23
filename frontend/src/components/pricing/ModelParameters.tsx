// src/components/pricing/ModelParameters.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';
import FormField from '../common/FormField';
import { getModelById, ModelParameter } from '../../config/pricingConfig';

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
      [paramId]: value,
    });
  };

  const renderParameterField = (param: ModelParameter) => {
    if (param.type === 'boolean') {
      return (
        <div key={param.id} className="col-span-6 sm:col-span-3">
          <label htmlFor={param.id} className="block text-sm font-medium text-white">
            {param.name}
          </label>
          <input
            id={param.id}
            type="checkbox"
            className="mt-1 focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"
            checked={config.model_params[param.id] ?? param.defaultValue}
            onChange={(e) => handleModelParamChange(param.id, e.target.checked)}
          />
          {param.helperText && <p className="mt-1 text-gray-500 text-xs">{param.helperText}</p>}
        </div>
      );
    } else {
      return (
        <FormField
          key={param.id}
          label={param.name}
          type={param.type as 'number' | 'text' | 'date' | 'select'} // Type assertion
          value={config.model_params[param.id] ?? param.defaultValue}
          onChange={(value) => handleModelParamChange(param.id, value)}
          min={param.min}
          max={param.max}
          step={param.step}
          options={param.options}
          helperText={param.helperText}
          size="sm"
        />
      );
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-base font-semibold text-white mb-3">
        {selectedModel.name} Model Parameters
      </h3>

      <div className="grid grid-cols-6 gap-3">
        {selectedModel.parameters.map(renderParameterField)}
      </div>
    </div>
  );
};

export default ModelParameters;
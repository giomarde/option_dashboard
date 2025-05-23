// src/components/pricing/PricingForm.tsx
import React, { useState } from 'react';
import { PricingConfig } from '../Pricer';
import ContractSpecifications from './ContractSpecifications';
import DeliverySchedule from './DeliverySchedule';
import PricingParameters from './PricingParameters';
import ModelParameters from './ModelParameters';
import AdvancedSettings from './AdvancedSettings';

interface PricingFormProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const PricingForm: React.FC<PricingFormProps> = ({ config, onConfigChange }) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div className="space-y-3">
      {/* Contract Specifications */}
      <ContractSpecifications 
        config={config} 
        onConfigChange={onConfigChange} 
      />

      {/* Delivery Schedule */}
      <DeliverySchedule 
        config={config} 
        onConfigChange={onConfigChange} 
      />

      {/* Pricing Parameters */}
      <PricingParameters 
        config={config} 
        onConfigChange={onConfigChange} 
      />

      {/* Advanced Settings Toggle */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between text-left"
        >
          <div>
            <h3 className="text-base font-semibold text-white">Advanced Settings</h3>
            <p className="text-gray-400 text-xs">Monte Carlo configuration and additional parameters</p>
          </div>
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
              showAdvanced ? 'transform rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {showAdvanced && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <AdvancedSettings 
              config={config} 
              onConfigChange={onConfigChange} 
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default PricingForm;
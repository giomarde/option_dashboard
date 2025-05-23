// src/components/pricing/PricingForm.tsx
import React, { useState } from 'react';
import { PricingConfig } from '../Pricer';
import ContractSpecifications from './ContractSpecifications';
import DeliverySchedule from './DeliverySchedule';
import PricingParameters from './PricingParameters';
import AdvancedSettings from './AdvancedSettings';

interface PricingFormProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const PricingForm: React.FC<PricingFormProps> = ({ config, onConfigChange }) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div className="space-y-6">
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
      <div className="bg-gray-800 border-2 border-gray-700 p-6">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between text-left"
        >
          <div className="flex items-center space-x-3">
            <span className="text-2xl">⚙️</span>
            <div>
              <h3 className="text-lg font-semibold text-white">Advanced Settings</h3>
              <p className="text-gray-400 text-sm">Monte Carlo configuration and additional parameters</p>
            </div>
          </div>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${
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
          <div className="mt-6 pt-6 border-t-2 border-gray-700">
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
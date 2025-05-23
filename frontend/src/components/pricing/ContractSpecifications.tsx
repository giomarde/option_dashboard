// src/components/pricing/ContractSpecifications.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';
import FormField from '../common/FormField';

interface ContractSpecificationsProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const ContractSpecifications: React.FC<ContractSpecificationsProps> = ({ config, onConfigChange }) => {
  return (
    <div className="bg-gray-800 border-2 border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-white mb-6 pb-3 border-b-2 border-gray-700">
        Contract Specifications
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FormField
          label="Option Type"
          type="select"
          value={config.option_type}
          onChange={(value) => onConfigChange('option_type', value)}
          options={[
            { value: 'call', label: 'Call Option' },
            { value: 'put', label: 'Put Option' }
          ]}
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
        />

        <FormField
          label="Primary Index"
          type="select"
          value={config.primary_index}
          onChange={(value) => onConfigChange('primary_index', value)}
          options={[
            { value: 'THE', label: 'THE (TTF)' },
            { value: 'JKM', label: 'JKM' },
            { value: 'DES', label: 'DES (LNG DES)' }
          ]}
        />

        <FormField
          label="Secondary Index"
          type="select"
          value={config.secondary_index}
          onChange={(value) => onConfigChange('secondary_index', value)}
          options={[
            { value: 'TFU', label: 'TFU (LNG TFU)' },
            { value: 'THE', label: 'THE (TTF)' },
            { value: 'DES', label: 'DES (LNG DES)' }
          ]}
        />

        <FormField
          label="Output Unit"
          type="select"
          value={config.output_unit}
          onChange={(value) => onConfigChange('output_unit', value)}
          options={[
            { value: 'USD/MMBtu', label: 'USD/MMBtu' },
            { value: 'EUR/MWh', label: 'EUR/MWh' }
          ]}
        />

        <FormField
          label="Cargo Volume"
          type="number"
          value={config.cargo_volume}
          onChange={(value) => onConfigChange('cargo_volume', Number(value))}
          step={1000}
          min={0}
        />
      </div>

      {/* Option Description */}
      <div className="mt-6 p-4 bg-gray-750 border-2 border-gray-600">
        <p className="text-sm text-gray-300">
          <strong className="text-white">Option Description:</strong>{' '}
          {config.option_type === 'call' 
            ? `Right to switch from ${config.secondary_index} to ${config.primary_index}` 
            : `Right to switch from ${config.primary_index} to ${config.secondary_index}`
          }
          {' '}for delivery of {config.cargo_volume.toLocaleString()} MMBtu.
        </p>
      </div>
    </div>
  );
};

export default ContractSpecifications;
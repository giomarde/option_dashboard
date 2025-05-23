// src/components/pricing/ContractSpecifications.tsx
import React, { useState } from 'react';
import { PricingConfig } from '../Pricer';
import FormField from '../common/FormField';
import { PHYSICAL_DEALS, OPTION_TYPES, getPhysicalDealById } from '../../config/pricingConfig';

interface ContractSpecificationsProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const ContractSpecifications: React.FC<ContractSpecificationsProps> = ({ config, onConfigChange }) => {
  const [showAdvancedMode, setShowAdvancedMode] = useState(false);
  
  const selectedDeal = getPhysicalDealById(config.deal_type);
  
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold text-white">Contract Specifications</h3>
        <label className="flex items-center space-x-2 text-xs">
          <input
            type="checkbox"
            checked={showAdvancedMode}
            onChange={(e) => setShowAdvancedMode(e.target.checked)}
            className="rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
          />
          <span className="text-gray-400">Advanced Mode</span>
        </label>
      </div>
      
      <div className="grid grid-cols-6 gap-3">
        {/* Deal Type / Option Type Selection */}
        {!showAdvancedMode ? (
          <div className="col-span-2">
            <FormField
              label="Deal Type"
              type="select"
              value={config.deal_type}
              onChange={(value) => onConfigChange('deal_type', value)}
              options={PHYSICAL_DEALS.map(d => ({ value: d.id, label: d.name }))}
              size="sm"
            />
          </div>
        ) : (
          <>
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
          </>
        )}

        <FormField
          label="Primary Index"
          type="select"
          value={config.primary_index}
          onChange={(value) => onConfigChange('primary_index', value)}
          options={[
            { value: 'THE', label: 'THE (TTF)' },
            { value: 'JKM', label: 'JKM' },
            { value: 'DES', label: 'DES (LNG)' }
          ]}
          size="sm"
        />

        <FormField
          label="Secondary Index"
          type="select"
          value={config.secondary_index}
          onChange={(value) => onConfigChange('secondary_index', value)}
          options={[
            { value: 'TFU', label: 'TFU (LNG)' },
            { value: 'THE', label: 'THE (TTF)' },
            { value: 'DES', label: 'DES (LNG)' }
          ]}
          size="sm"
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
          size="sm"
        />

        <FormField
          label="Cargo Volume"
          type="number"
          value={config.cargo_volume}
          onChange={(value) => onConfigChange('cargo_volume', Number(value))}
          step={1000}
          min={0}
          size="sm"
        />
      </div>

      {/* Option Description */}
      <div className="mt-3 p-2 bg-gray-750 rounded-md">
        <p className="text-xs text-gray-300">
          <strong className="text-white">{selectedDeal?.name || 'Option'}:</strong>{' '}
          {config.option_type === 'vanilla_spread' 
            ? `Right to switch from ${config.secondary_index} to ${config.primary_index}` 
            : `Option on ${config.primary_index}`
          }
          {' '}for {config.cargo_volume.toLocaleString()} MMBtu.
          {showAdvancedMode && (
            <span className="text-gray-400 ml-2">
              (Mathematical: {config.option_type.replace('_', ' ')})
            </span>
          )}
        </p>
      </div>
    </div>
  );
};

export default ContractSpecifications;
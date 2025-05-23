// src/components/pricing/ContractSpecifications.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';
import FormField from '../common/FormField';
import { PHYSICAL_DEALS, getPhysicalDealById } from '../../config/pricingConfig';

interface ContractSpecificationsProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const ContractSpecifications: React.FC<ContractSpecificationsProps> = ({ config, onConfigChange }) => {
  const selectedDeal = getPhysicalDealById(config.deal_type);
  
  const handleDealTypeChange = (value: string | number) => {
    // Convert to string if needed
    const dealType = value.toString();
    
    // If geographical arbitrage is selected, we may need to set up additional indices
    onConfigChange('deal_type', dealType);
    
    // Add functionality for geographical arbitrage to add more indices
    if (dealType === 'geographical_arbitrage') {
      // Initialize with 3 indices (could be expanded based on user interaction)
      onConfigChange('basket_indices', ['THE', 'JKM', 'DES']);
    }
  };
  
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <div className="mb-3">
        <h3 className="text-base font-semibold text-white">Contract Specifications</h3>
      </div>
      
      <div className="grid grid-cols-6 gap-3">
        {/* Deal Type Selection */}
        <div className="col-span-2">
          <FormField
            label="Deal Type"
            type="select"
            value={config.deal_type}
            onChange={handleDealTypeChange}
            options={PHYSICAL_DEALS.map(d => ({ value: d.id, label: d.name }))}
            size="sm"
          />
        </div>

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

        {config.deal_type !== 'geographical_arbitrage' ? (
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
        ) : (
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-300 mb-1">Basket Indices</label>
            <div className="flex gap-1">
              {config.basket_indices.map((index, i) => (
                <span key={i} className="px-2 py-1 bg-gray-700 text-white text-xs rounded-md">
                  {index}
                </span>
              ))}
              <button 
                className="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white text-xs rounded-md"
                onClick={() => {
                  const availableIndices = ['THE', 'JKM', 'DES', 'TFU', 'NBP', 'HH'];
                  const currentIndices = config.basket_indices || [];
                  
                  // Find an index that's not already in the basket
                  const newIndex = availableIndices.find(idx => !currentIndices.includes(idx));
                  
                  if (newIndex) {
                    onConfigChange('basket_indices', [...currentIndices, newIndex]);
                  }
                }}
              >
                + Add
              </button>
            </div>
          </div>
        )}

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
        </p>
      </div>
    </div>
  );
};

export default ContractSpecifications;
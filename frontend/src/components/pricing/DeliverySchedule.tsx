// src/components/pricing/DeliverySchedule.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';
import FormField from '../common/FormField';

interface DeliveryScheduleProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const DeliverySchedule: React.FC<DeliveryScheduleProps> = ({ config, onConfigChange }) => {
  const monthOptions = [
    { value: 'Jan', label: 'Jan' },
    { value: 'Feb', label: 'Feb' },
    { value: 'Mar', label: 'Mar' },
    { value: 'Apr', label: 'Apr' },
    { value: 'May', label: 'May' },
    { value: 'Jun', label: 'Jun' },
    { value: 'Jul', label: 'Jul' },
    { value: 'Aug', label: 'Aug' },
    { value: 'Sep', label: 'Sep' },
    { value: 'Oct', label: 'Oct' },
    { value: 'Nov', label: 'Nov' },
    { value: 'Dec', label: 'Dec' },
  ];

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-base font-semibold text-white mb-3">Delivery Schedule</h3>
      
      <div className="grid grid-cols-6 gap-3">
        <FormField
          label="Evaluation Date"
          type="date"
          value={config.evaluation_date}
          onChange={(value) => onConfigChange('evaluation_date', value)}
          required
          size="sm"
        />

        <FormField
          label="# Options"
          type="number"
          value={config.num_options}
          onChange={(value) => onConfigChange('num_options', Number(value))}
          min={1}
          max={12}
          required
          size="sm"
        />

        <FormField
          label="First Month"
          type="select"
          value={config.first_delivery_month}
          onChange={(value) => onConfigChange('first_delivery_month', value)}
          options={monthOptions}
          size="sm"
        />

        <FormField
          label="Year"
          type="number"
          value={config.first_delivery_year}
          onChange={(value) => onConfigChange('first_delivery_year', Number(value))}
          min={2024}
          max={2030}
          required
          size="sm"
        />

        <FormField
          label="Delivery Day"
          type="number"
          value={config.delivery_day}
          onChange={(value) => onConfigChange('delivery_day', Number(value))}
          min={1}
          max={31}
          size="sm"
        />

        <FormField
          label="Decision Days Prior"
          type="number"
          value={config.decision_days_prior}
          onChange={(value) => onConfigChange('decision_days_prior', Number(value))}
          min={1}
          max={90}
          size="sm"
        />
      </div>

      {/* Compact Summary */}
      <div className="mt-3 flex items-center justify-between text-xs text-gray-400 bg-gray-750 rounded-md p-2">
        <span>
          First: {config.first_delivery_month} {config.delivery_day}, {config.first_delivery_year}
        </span>
        <span className="text-gray-300">•</span>
        <span>
          Total: {config.num_options} options
        </span>
        <span className="text-gray-300">•</span>
        <span>
          Volume: {(config.cargo_volume * config.num_options).toLocaleString()} MMBtu
        </span>
      </div>
    </div>
  );
};

export default DeliverySchedule;
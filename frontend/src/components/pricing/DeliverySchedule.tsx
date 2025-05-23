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
    { value: 'Jan', label: 'January' },
    { value: 'Feb', label: 'February' },
    { value: 'Mar', label: 'March' },
    { value: 'Apr', label: 'April' },
    { value: 'May', label: 'May' },
    { value: 'Jun', label: 'June' },
    { value: 'Jul', label: 'July' },
    { value: 'Aug', label: 'August' },
    { value: 'Sep', label: 'September' },
    { value: 'Oct', label: 'October' },
    { value: 'Nov', label: 'November' },
    { value: 'Dec', label: 'December' },
  ];

  return (
    <div className="bg-gray-800 border-2 border-gray-700 p-6">
      <h3 className="text-lg font-semibold text-white mb-6 pb-3 border-b-2 border-gray-700">
        Delivery Schedule
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <FormField
          label="Evaluation Date"
          type="date"
          value={config.evaluation_date}
          onChange={(value) => onConfigChange('evaluation_date', value)}
          required
        />

        <FormField
          label="Number of Options"
          type="number"
          value={config.num_options}
          onChange={(value) => onConfigChange('num_options', Number(value))}
          min={1}
          max={12}
          required
        />

        <FormField
          label="First Delivery Month"
          type="select"
          value={config.first_delivery_month}
          onChange={(value) => onConfigChange('first_delivery_month', value)}
          options={monthOptions}
        />

        <FormField
          label="First Delivery Year"
          type="number"
          value={config.first_delivery_year}
          onChange={(value) => onConfigChange('first_delivery_year', Number(value))}
          min={2024}
          max={2030}
          required
        />

        <FormField
          label="Delivery Day"
          type="number"
          value={config.delivery_day}
          onChange={(value) => onConfigChange('delivery_day', Number(value))}
          min={1}
          max={31}
          helperText="Day of month for delivery"
        />

        <FormField
          label="Decision Days Prior"
          type="number"
          value={config.decision_days_prior}
          onChange={(value) => onConfigChange('decision_days_prior', Number(value))}
          min={1}
          max={90}
          helperText="Days before delivery for decision"
        />
      </div>

      {/* Delivery Summary */}
      <div className="mt-6 p-4 bg-gray-750 border-2 border-gray-600">
        <h4 className="text-sm font-semibold text-white mb-2">Delivery Summary</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-400">First Delivery:</span>
            <span className="text-white ml-2">
              {config.first_delivery_month} {config.delivery_day}, {config.first_delivery_year}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Total Options:</span>
            <span className="text-white ml-2">{config.num_options}</span>
          </div>
          <div>
            <span className="text-gray-400">Total Volume:</span>
            <span className="text-white ml-2">
              {(config.cargo_volume * config.num_options).toLocaleString()} MMBtu
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeliverySchedule;
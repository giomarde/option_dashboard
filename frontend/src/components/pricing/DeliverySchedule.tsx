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

  const frequencyOptions = [
    { value: 'single', label: 'Single' },
    { value: 'weekly', label: 'Weekly' },
    { value: 'biweekly', label: 'Bi-Weekly' },
    { value: 'monthly', label: 'Monthly' },
    { value: 'quarterly', label: 'Quarterly' },
    { value: 'semiannual', label: 'Semi-Annual' },
    { value: 'annual', label: 'Annual' },
  ];

  const contractTypeOptions = [
    { value: 'single', label: 'Single' },
    { value: 'term', label: 'Term' },
  ];

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-base font-semibold text-white mb-3">Delivery Schedule</h3>
      
      <div className="grid grid-cols-6 gap-3">
        <FormField
          label="Delivery Date"
          type="date"
          value={config.evaluation_date}
          onChange={(value) => onConfigChange('evaluation_date', value)}
          required
          size="sm"
        />

        <FormField
          label="Contract Type"
          type="select"
          value={config.contract_type || 'single'}
          onChange={(value) => onConfigChange('contract_type', value)}
          options={contractTypeOptions}
          size="sm"
        />

        <FormField
          label="Frequency"
          type="select"
          value={config.frequency || 'monthly'}
          onChange={(value) => onConfigChange('frequency', value)}
          options={frequencyOptions}
          disabled={config.contract_type !== 'term'}
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
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-400 bg-gray-750 rounded-md p-2">
        <div>
          <span>First: {config.first_delivery_month} {config.delivery_day}, {config.first_delivery_year}</span>
        </div>
        <div>
          <span>Total: {config.num_options} options</span>
        </div>
        <div>
          <span>Contract: {config.contract_type || 'Single'}</span>
          {config.contract_type === 'term' && (
            <span className="ml-1">({config.frequency || 'Monthly'})</span>
          )}
        </div>
        <div>
          <span>Volume: {(config.cargo_volume * config.num_options).toLocaleString()} MMBtu</span>
        </div>
      </div>
    </div>
  );
};

export default DeliverySchedule;
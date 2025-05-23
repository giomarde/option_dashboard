// src/components/common/FormField.tsx
import React from 'react';

interface Option {
  value: string | number;
  label: string;
}

interface FormFieldProps {
  label: string;
  type: 'text' | 'number' | 'date' | 'select';
  value: string | number;
  onChange: (value: string | number) => void;
  options?: Option[];
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  helperText?: string;
  size?: 'sm' | 'md' | 'lg';
}

const FormField: React.FC<FormFieldProps> = ({
  label,
  type,
  value,
  onChange,
  options,
  min,
  max,
  step,
  placeholder,
  required = false,
  disabled = false,
  helperText,
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-2 text-sm',
    lg: 'px-4 py-3 text-base'
  };

  const baseClasses = `
    w-full ${sizeClasses[size]} bg-gray-700 border border-gray-600 text-white
    rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500
    transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
  `;

  const renderInput = () => {
    switch (type) {
      case 'select':
        return (
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            required={required}
            className={baseClasses}
          >
            {options?.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      case 'number':
        return (
          <input
            type="number"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            min={min}
            max={max}
            step={step}
            placeholder={placeholder}
            disabled={disabled}
            required={required}
            className={baseClasses}
          />
        );

      case 'date':
        return (
          <input
            type="date"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            required={required}
            className={baseClasses}
          />
        );

      default:
        return (
          <input
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            required={required}
            className={baseClasses}
          />
        );
    }
  };

  return (
    <div className="space-y-1">
      <label className={`block ${size === 'sm' ? 'text-xs' : 'text-sm'} font-medium text-gray-300`}>
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      
      {renderInput()}
      
      {helperText && (
        <p className="text-xs text-gray-400 mt-1">{helperText}</p>
      )}
    </div>
  );
};

export default FormField;
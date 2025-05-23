// src/components/pricing/AdvancedSettings.tsx
import React from 'react';
import { PricingConfig } from '../Pricer';
import FormField from '../common/FormField';

interface AdvancedSettingsProps {
  config: PricingConfig;
  onConfigChange: (field: string, value: any) => void;
}

const AdvancedSettings: React.FC<AdvancedSettingsProps> = ({ config, onConfigChange }) => {
  return (
    <div className="space-y-4">
      {/* Monte Carlo Settings */}
      <div>
        <h4 className="text-sm font-semibold text-white mb-2">Monte Carlo Simulation</h4>
        <div className="grid grid-cols-3 gap-3">
          <FormField
            label="Run Monte Carlo"
            type="select"
            value={config.run_monte_carlo ? 'true' : 'false'}
            onChange={(value) => onConfigChange('run_monte_carlo', value === 'true')}
            options={[
              { value: 'true', label: 'Yes' },
              { value: 'false', label: 'No' }
            ]}
            size="sm"
          />

          <FormField
            label="Number of Paths"
            type="number"
            value={config.mc_paths}
            onChange={(value) => onConfigChange('mc_paths', Number(value))}
            min={1000}
            max={100000}
            step={1000}
            disabled={!config.run_monte_carlo}
            helperText="More paths = higher accuracy"
            size="sm"
          />

          <FormField
            label="Random Seed"
            type="number"
            value={config.mc_seed}
            onChange={(value) => onConfigChange('mc_seed', Number(value))}
            min={1}
            max={999999}
            disabled={!config.run_monte_carlo}
            helperText="For reproducible results"
            size="sm"
          />
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="p-3 bg-gray-750 rounded-md">
        <div className="grid grid-cols-3 gap-3 text-xs">
          <div>
            <span className="text-gray-400">Runtime:</span>
            <div className="text-white font-medium">
              {config.run_monte_carlo 
                ? `~${Math.ceil(config.mc_paths / 5000)}s`
                : '< 1s'
              }
            </div>
          </div>
          <div>
            <span className="text-gray-400">Memory:</span>
            <div className="text-white font-medium">
              {config.run_monte_carlo 
                ? `~${Math.ceil(config.mc_paths * config.num_options / 1000)} MB`
                : '< 1 MB'
              }
            </div>
          </div>
          <div>
            <span className="text-gray-400">Accuracy:</span>
            <div className="text-white font-medium">
              {config.run_monte_carlo 
                ? `±${(1.96 / Math.sqrt(config.mc_paths) * 100).toFixed(2)}%`
                : 'Exact'
              }
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdvancedSettings;
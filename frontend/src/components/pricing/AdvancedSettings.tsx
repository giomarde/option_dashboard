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
    <div className="space-y-6">
      {/* Monte Carlo Settings */}
      <div>
        <h4 className="text-md font-semibold text-white mb-4">Monte Carlo Simulation</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FormField
            label="Run Monte Carlo"
            type="select"
            value={config.run_monte_carlo ? 'true' : 'false'}
            onChange={(value) => onConfigChange('run_monte_carlo', value === 'true')}
            options={[
              { value: 'true', label: 'Yes' },
              { value: 'false', label: 'No' }
            ]}
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
          />
        </div>
      </div>

      {/* Performance Warning */}
      {config.run_monte_carlo && config.mc_paths > 50000 && (
        <div className="p-4 bg-yellow-900 bg-opacity-30 border-2 border-yellow-600 text-yellow-200">
          <div className="flex items-center space-x-2">
            <span className="text-yellow-400">⚠️</span>
            <div>
              <p className="font-medium">High Path Count Warning</p>
              <p className="text-sm text-yellow-300">
                Using {config.mc_paths.toLocaleString()} paths may take several minutes to compute.
                Consider using 10,000-25,000 paths for faster results.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Computational Complexity Info */}
      <div className="p-4 bg-gray-750 border-2 border-gray-600">
        <h5 className="text-sm font-semibold text-white mb-2">Computational Complexity</h5>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-gray-400">
          <div>
            <span className="text-gray-300">Estimated Runtime:</span>
            <div className="mt-1">
              {config.run_monte_carlo 
                ? `~${Math.ceil(config.mc_paths / 5000)} seconds`
                : '< 1 second (Analytical)'
              }
            </div>
          </div>
          <div>
            <span className="text-gray-300">Memory Usage:</span>
            <div className="mt-1">
              {config.run_monte_carlo 
                ? `~${Math.ceil(config.mc_paths * config.num_options / 1000)} MB`
                : '< 1 MB'
              }
            </div>
          </div>
          <div>
            <span className="text-gray-300">Accuracy:</span>
            <div className="mt-1">
              {config.run_monte_carlo 
                ? `±${(1.96 / Math.sqrt(config.mc_paths) * 100).toFixed(3)}%`
                : 'Exact (Analytical)'
              }
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdvancedSettings;
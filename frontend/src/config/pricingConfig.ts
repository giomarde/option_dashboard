// src/config/pricingConfig.ts

export interface PricingModel {
  id: string;
  name: string;
  description: string;
  supportedOptionTypes: string[];
  parameters: ModelParameter[];
}

export interface ModelParameter {
  id: string;
  name: string;
  type: 'number' | 'boolean' | 'select';
  defaultValue: any;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string; label: string }[];
  helperText?: string;
}

export interface OptionType {
  id: string;
  name: string;
  description: string;
  supportedModels: string[];
}

export interface PhysicalDeal {
  id: string;
  name: string;
  description: string;
  underlyingOptionType: string;
  additionalParams?: ModelParameter[];
}

// Pricing Models Definition
export const PRICING_MODELS: PricingModel[] = [
  {
    id: 'bachelier',
    name: 'Bachelier',
    description: 'Normal model for spread options',
    supportedOptionTypes: ['vanilla_spread'],
    parameters: [
      {
        id: 'volatility',
        name: 'Volatility',
        type: 'number',
        defaultValue: 0.3,
        min: 0.01,
        max: 2.0,
        step: 0.01,
        helperText: 'Annualized normal volatility'
      }
    ]
  },
  {
    id: 'dempster',
    name: 'Dempster',
    description: 'Long-term spread option model with mean reversion',
    supportedOptionTypes: ['vanilla_spread'],
    parameters: [
      {
        id: 'mean_reversion',
        name: 'Mean Reversion Speed',
        type: 'number',
        defaultValue: 0.5,
        min: 0.0,
        max: 5.0,
        step: 0.1,
        helperText: 'Speed of mean reversion (kappa)'
      },
      {
        id: 'long_term_spread',
        name: 'Long Term Spread',
        type: 'number',
        defaultValue: 0.0,
        min: -10.0,
        max: 10.0,
        step: 0.1,
        helperText: 'Long-term equilibrium spread level'
      },
      {
        id: 'volatility',
        name: 'Volatility',
        type: 'number',
        defaultValue: 0.3,
        min: 0.01,
        max: 2.0,
        step: 0.01,
        helperText: 'Spread volatility'
      }
    ]
  },
  {
    id: 'quadratic_normal',
    name: 'Quadratic Normal',
    description: 'Quadratic approximation for vanilla options',
    supportedOptionTypes: ['vanilla'],
    parameters: [
      {
        id: 'volatility',
        name: 'Volatility',
        type: 'number',
        defaultValue: 0.3,
        min: 0.01,
        max: 2.0,
        step: 0.01,
        helperText: 'Annualized volatility'
      },
      {
        id: 'skew',
        name: 'Volatility Skew',
        type: 'number',
        defaultValue: 0.0,
        min: -1.0,
        max: 1.0,
        step: 0.01,
        helperText: 'Quadratic skew parameter'
      }
    ]
  },
  {
    id: 'miltersen',
    name: 'Miltersen',
    description: 'Full stochastic model for energy options',
    supportedOptionTypes: ['vanilla', 'vanilla_spread'],
    parameters: [
      {
        id: 'volatility_1',
        name: 'Volatility (Index 1)',
        type: 'number',
        defaultValue: 0.3,
        min: 0.01,
        max: 2.0,
        step: 0.01,
        helperText: 'First index volatility'
      },
      {
        id: 'volatility_2',
        name: 'Volatility (Index 2)',
        type: 'number',
        defaultValue: 0.3,
        min: 0.01,
        max: 2.0,
        step: 0.01,
        helperText: 'Second index volatility (for spread options)'
      },
      {
        id: 'correlation',
        name: 'Correlation',
        type: 'number',
        defaultValue: 0.8,
        min: -1.0,
        max: 1.0,
        step: 0.01,
        helperText: 'Correlation between indices'
      },
      {
        id: 'mean_reversion_1',
        name: 'Mean Reversion (Index 1)',
        type: 'number',
        defaultValue: 0.5,
        min: 0.0,
        max: 5.0,
        step: 0.1
      },
      {
        id: 'mean_reversion_2',
        name: 'Mean Reversion (Index 2)',
        type: 'number',
        defaultValue: 0.5,
        min: 0.0,
        max: 5.0,
        step: 0.1
      }
    ]
  }
];

// Option Types Definition
export const OPTION_TYPES: OptionType[] = [
  {
    id: 'vanilla',
    name: 'Vanilla Option',
    description: 'Standard option on a single index',
    supportedModels: ['quadratic_normal', 'miltersen']
  },
  {
    id: 'vanilla_spread',
    name: 'Vanilla Spread Option',
    description: 'Option on the spread between two indices',
    supportedModels: ['bachelier', 'dempster', 'miltersen']
  },
  {
    id: 'basket_best_of',
    name: 'Best-of Basket',
    description: 'Option on the best performing index in a basket',
    supportedModels: [] // To be implemented
  }
];

// Physical Deal Types Definition
export const PHYSICAL_DEALS: PhysicalDeal[] = [
  {
    id: 'regasification',
    name: 'Regasification Option',
    description: 'Option to regasify LNG at a terminal',
    underlyingOptionType: 'vanilla_spread',
    additionalParams: [
      {
        id: 'regas_capacity',
        name: 'Terminal Capacity',
        type: 'number',
        defaultValue: 1000000,
        min: 0,
        step: 1000,
        helperText: 'Daily regasification capacity (MMBtu/day)'
      },
      {
        id: 'regas_efficiency',
        name: 'Regasification Efficiency',
        type: 'number',
        defaultValue: 0.98,
        min: 0.9,
        max: 1.0,
        step: 0.01,
        helperText: 'Energy efficiency of regasification'
      }
    ]
  },
  {
    id: 'cancellation',
    name: 'Cancellation Option',
    description: 'Option to cancel cargo delivery',
    underlyingOptionType: 'vanilla',
    additionalParams: [
      {
        id: 'cancellation_fee',
        name: 'Cancellation Fee',
        type: 'number',
        defaultValue: 0.5,
        min: 0,
        step: 0.01,
        helperText: 'Fixed fee for cancellation (USD/MMBtu)'
      },
      {
        id: 'notice_period',
        name: 'Notice Period (Days)',
        type: 'number',
        defaultValue: 30,
        min: 1,
        max: 90,
        step: 1,
        helperText: 'Days notice required for cancellation'
      }
    ]
  },
  {
    id: 'geographical_arbitrage',
    name: 'Geographical Arbitrage',
    description: 'Option to deliver to best location',
    underlyingOptionType: 'basket_best_of',
    additionalParams: [
      {
        id: 'num_locations',
        name: 'Number of Locations',
        type: 'number',
        defaultValue: 3,
        min: 2,
        max: 5,
        step: 1,
        helperText: 'Number of delivery locations'
      },
      {
        id: 'transport_costs',
        name: 'Transport Cost Mode',
        type: 'select',
        defaultValue: 'fixed',
        options: [
          { value: 'fixed', label: 'Fixed Cost' },
          { value: 'distance_based', label: 'Distance Based' },
          { value: 'market_based', label: 'Market Based' }
        ]
      }
    ]
  }
];

// Helper functions
export const getModelById = (id: string): PricingModel | undefined => 
  PRICING_MODELS.find(m => m.id === id);

export const getOptionTypeById = (id: string): OptionType | undefined => 
  OPTION_TYPES.find(t => t.id === id);

export const getPhysicalDealById = (id: string): PhysicalDeal | undefined => 
  PHYSICAL_DEALS.find(d => d.id === id);

export const getCompatibleModels = (optionType: string): PricingModel[] => 
  PRICING_MODELS.filter(m => m.supportedOptionTypes.includes(optionType));

export const getCompatibleOptionTypes = (modelId: string): OptionType[] => {
  const model = getModelById(modelId);
  if (!model) return [];
  return OPTION_TYPES.filter(t => model.supportedOptionTypes.includes(t.id));
};
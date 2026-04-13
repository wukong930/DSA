import apiClient from './index';
import { toCamelCase } from './utils';

export interface StrategyBtRunSummary {
  id: number;
  userId: number;
  strategyName: string;
  codes: string[];
  startDate: string | null;
  endDate: string | null;
  freq: string;
  status: string;
  progress: string | null;
  totalReturnPct: number | null;
  sharpeRatio: number | null;
  maxDrawdownPct: number | null;
  winRatePct: number | null;
  totalTrades: number | null;
  createdAt: string | null;
  startedAt: string | null;
  completedAt: string | null;
  errorMessage: string | null;
}

export interface StrategyBtRunDetail extends StrategyBtRunSummary {
  strategyParams: Record<string, unknown>;
  initialCash: number;
  commission: number;
  benchmark: string;
  result: StrategyBtResult | null;
}

export interface StrategyBtTrade {
  code: string;
  entryDate: string;
  entryPrice: number | null;
  exitDate: string;
  exitPrice: number | null;
  returnPct: number;
  holdingDays: number;
  pnl: number;
  positionValue: number | null;
  highPrice: number | null;
  lowPrice: number | null;
  entrySignal: string | null;
  exitReason: string | null;
  benchEntry: number | null;
  benchExit: number | null;
  relativeReturn: number | null;
}

export interface StrategyBtResult {
  totalReturnPct: number;
  annualReturnPct: number;
  sharpeRatio: number;
  sortinoRatio: number;
  calmarRatio: number;
  maxDrawdownPct: number;
  maxDrawdownDurationDays: number;
  winRatePct: number;
  profitLossRatio: number;
  volatilityAnnual: number;
  var95: number;
  cvar95: number;
  informationRatio: number | null;
  beta: number | null;
  alpha: number | null;
  totalTrades: number;
  avgHoldingDays: number;
  avgProfitPerTrade: number;
  maxConsecutiveWins: number;
  maxConsecutiveLosses: number;
  factorIc: Record<string, number> | null;
  factorIr: Record<string, number> | null;
  equityCurve: Array<{ date: string; value: number; benchmark?: number }>;
  drawdownCurve: Array<{ date: string; drawdownPct: number }>;
  monthlyReturns: Array<{ year: number; month: number; returnPct: number }>;
  tradeList: StrategyBtTrade[];
  benchmarkWarning: string | null;
  warnings: string[];
  rebalanceHistory: Array<{ window: number; start: string; end: string; codes: string[]; totalCodes: number }>;
  skippedCodes: string[];
  textReport: string;
}

export interface StrategyInfo {
  name: string;
  description: string;
}

export interface FactorInfo {
  name: string;
  description: string;
}

export interface CustomStrategyInfo {
  name: string;
  buyExpression: string;
  sellExpression: string;
  description: string;
}

export interface DatasetInfo {
  name: string;
  path: string;
  freq: string;
  source: string;
  dateRange: string[];
  codeCount: number;
}

export interface StrategyBtRunRequest {
  strategyName: string;
  codes: string[];
  startDate: string;
  endDate: string;
  strategyParams?: Record<string, unknown>;
  freq?: string;
  initialCash?: number;
  commission?: number;
  slippage?: number;
  benchmark?: string;
  screenUniverse?: boolean;
  screenFactors?: string[];
  screenTopN?: number;
  screenLookbackDays?: number;
  rebalanceDays?: number;
  stopLossPct?: number | null;
  takeProfitPct?: number | null;
  allowShort?: boolean;
}

export const strategyBtApi = {
  submit: async (data: StrategyBtRunRequest): Promise<{ runId: number }> => {
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/strategy-bt/run', {
      strategy_name: data.strategyName,
      strategy_params: data.strategyParams ?? {},
      codes: data.codes,
      start_date: data.startDate,
      end_date: data.endDate,
      freq: data.freq ?? '1d',
      initial_cash: data.initialCash ?? 1000000,
      commission: data.commission ?? 0.001,
      slippage: data.slippage ?? 0.001,
      benchmark: data.benchmark ?? '000300',
      screen_universe: data.screenUniverse ?? false,
      screen_factors: data.screenFactors ?? [],
      screen_top_n: data.screenTopN ?? 50,
      screen_lookback_days: data.screenLookbackDays ?? 60,
      rebalance_days: data.rebalanceDays ?? 0,
      stop_loss_pct: data.stopLossPct ?? null,
      take_profit_pct: data.takeProfitPct ?? null,
      allow_short: data.allowShort ?? false,
    });
    return toCamelCase(res.data);
  },

  listRuns: async (limit = 20, offset = 0): Promise<StrategyBtRunSummary[]> => {
    const res = await apiClient.get<Record<string, unknown>[]>('/api/v1/strategy-bt/runs', {
      params: { limit, offset },
    });
    return toCamelCase(res.data);
  },

  getRun: async (runId: number): Promise<StrategyBtRunDetail> => {
    const res = await apiClient.get<Record<string, unknown>>(`/api/v1/strategy-bt/runs/${runId}`);
    return toCamelCase(res.data);
  },

  listStrategies: async (): Promise<StrategyInfo[]> => {
    const res = await apiClient.get<Record<string, unknown>[]>('/api/v1/strategy-bt/strategies');
    return toCamelCase(res.data);
  },

  listFactors: async (): Promise<FactorInfo[]> => {
    const res = await apiClient.get<Record<string, unknown>[]>('/api/v1/strategy-bt/factors');
    return toCamelCase(res.data);
  },

  listDatasets: async (): Promise<DatasetInfo[]> => {
    const res = await apiClient.get<Record<string, unknown>[]>('/api/v1/strategy-bt/datasets');
    return toCamelCase(res.data);
  },

  uploadDataset: async (file: File, name: string, freq = '1d', source = 'custom'): Promise<{ message: string; filesCount: number; datasetName: string; failedFiles: string[] }> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    formData.append('freq', freq);
    formData.append('source', source);
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/strategy-bt/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000, // 5min for large files
    });
    return toCamelCase(res.data);
  },

  createCustomFactor: async (name: string, expression: string, description = ''): Promise<{ name: string; message: string }> => {
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/strategy-bt/factors/custom', {
      name, expression, description,
    });
    return toCamelCase(res.data);
  },

  listCustomFactors: async (): Promise<FactorInfo[]> => {
    const res = await apiClient.get<Record<string, unknown>[]>('/api/v1/strategy-bt/factors/custom');
    return toCamelCase(res.data);
  },

  deleteCustomFactor: async (factorName: string): Promise<void> => {
    await apiClient.delete(`/api/v1/strategy-bt/factors/custom/${factorName}`);
  },

  // Custom strategies
  validateExpression: async (expression: string): Promise<{ valid: boolean; error?: string; translated?: string }> => {
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/strategy-bt/strategies/custom/validate', { expression });
    return toCamelCase(res.data);
  },

  parseStrategyExpression: async (expression: string): Promise<{ buyExpression: string; sellExpression: string; translated?: string }> => {
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/strategy-bt/strategies/custom/parse', { expression });
    return toCamelCase(res.data);
  },

  createCustomStrategy: async (
    name: string, buyExpression: string, sellExpression: string, description = ''
  ): Promise<{ name: string; message: string }> => {
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/strategy-bt/strategies/custom', {
      name, buy_expression: buyExpression, sell_expression: sellExpression, description,
    });
    return toCamelCase(res.data);
  },

  listCustomStrategies: async (): Promise<CustomStrategyInfo[]> => {
    const res = await apiClient.get<Record<string, unknown>[]>('/api/v1/strategy-bt/strategies/custom');
    return toCamelCase(res.data);
  },

  deleteCustomStrategy: async (strategyName: string): Promise<void> => {
    await apiClient.delete(`/api/v1/strategy-bt/strategies/custom/${strategyName}`);
  },

  deleteRun: async (runId: number): Promise<void> => {
    await apiClient.delete(`/api/v1/strategy-bt/runs/${runId}`);
  },

  deleteDataset: async (name: string): Promise<void> => {
    await apiClient.delete(`/api/v1/strategy-bt/datasets/${name}`);
  },

  // Available codes from datasets
  listAvailableCodes: async (freq = '1d'): Promise<{ codes: string[]; count: number }> => {
    const res = await apiClient.get<Record<string, unknown>>('/api/v1/strategy-bt/codes', {
      params: { freq },
    });
    return toCamelCase(res.data);
  },
};

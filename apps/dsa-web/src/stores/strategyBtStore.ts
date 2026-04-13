import { create } from 'zustand';
import { strategyBtApi } from '../api/strategyBt';
import type {
  StrategyBtRunSummary,
  StrategyBtRunDetail,
  StrategyInfo,
  FactorInfo,
  DatasetInfo,
  StrategyBtRunRequest,
  CustomStrategyInfo,
} from '../api/strategyBt';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';

interface StrategyBtState {
  runs: StrategyBtRunSummary[];
  currentRun: StrategyBtRunDetail | null;
  strategies: StrategyInfo[];
  factors: FactorInfo[];
  customFactors: FactorInfo[];
  customStrategies: CustomStrategyInfo[];
  availableCodes: string[];
  datasets: DatasetInfo[];
  loading: boolean;
  initialLoading: boolean;
  submitting: boolean;
  uploading: boolean;
  error: ParsedApiError | null;
  warnings: string[];

  fetchRuns: (offset?: number) => Promise<void>;
  fetchRun: (id: number) => Promise<void>;
  submitBacktest: (config: StrategyBtRunRequest) => Promise<number | null>;
  fetchStrategies: () => Promise<void>;
  fetchFactors: () => Promise<void>;
  fetchCustomFactors: () => Promise<void>;
  fetchCustomStrategies: () => Promise<void>;
  fetchDatasets: () => Promise<void>;
  fetchAvailableCodes: (freq?: string) => Promise<void>;
  uploadDataset: (file: File, name: string, freq?: string, source?: string) => Promise<boolean>;
  createCustomFactor: (name: string, expression: string, description?: string) => Promise<boolean>;
  deleteCustomFactor: (name: string) => Promise<boolean>;
  createCustomStrategy: (name: string, buyExpr: string, sellExpr: string, description?: string) => Promise<boolean>;
  deleteCustomStrategy: (name: string) => Promise<boolean>;
  deleteRun: (runId: number) => Promise<boolean>;
  deleteDataset: (name: string) => Promise<boolean>;
  clearCurrentRun: () => void;
  clearWarnings: () => void;
  pollRun: (id: number) => Promise<boolean>;
  initializeData: () => Promise<void>;
  runsHasMore: boolean;
}

export const useStrategyBtStore = create<StrategyBtState>((set, get) => ({
  runs: [],
  currentRun: null,
  strategies: [],
  factors: [],
  customFactors: [],
  customStrategies: [],
  availableCodes: [],
  datasets: [],
  loading: false,
  initialLoading: false,
  submitting: false,
  uploading: false,
  error: null,
  warnings: [],
  runsHasMore: false,

  fetchRuns: async (offset = 0) => {
    set({ loading: true, error: null });
    try {
      const limit = 20;
      const runs = await strategyBtApi.listRuns(limit, offset);
      if (offset === 0) {
        set({ runs, runsHasMore: runs.length >= limit, loading: false });
      } else {
        set((s) => ({
          runs: [...s.runs, ...runs],
          runsHasMore: runs.length >= limit,
          loading: false,
        }));
      }
    } catch (e) {
      set({ error: getParsedApiError(e), loading: false });
    }
  },

  fetchRun: async (id: number) => {
    set({ loading: true, error: null });
    try {
      const run = await strategyBtApi.getRun(id);
      set({ currentRun: run, loading: false });
    } catch (e) {
      set({ error: getParsedApiError(e), loading: false });
    }
  },

  submitBacktest: async (config: StrategyBtRunRequest) => {
    set({ submitting: true, error: null });
    try {
      const { runId } = await strategyBtApi.submit(config);
      // Refresh list
      void get().fetchRuns();
      set({ submitting: false });
      return runId;
    } catch (e) {
      set({ error: getParsedApiError(e), submitting: false });
      return null;
    }
  },

  fetchStrategies: async () => {
    try {
      const strategies = await strategyBtApi.listStrategies();
      set({ strategies });
    } catch (e) {
      console.warn('Failed to fetch strategies:', e);
      set((s) => ({ warnings: [...s.warnings, '策略列表加载失败'] }));
    }
  },

  fetchFactors: async () => {
    try {
      const factors = await strategyBtApi.listFactors();
      set({ factors });
    } catch (e) {
      console.warn('Failed to fetch factors:', e);
      set((s) => ({ warnings: [...s.warnings, '因子列表加载失败'] }));
    }
  },

  fetchCustomFactors: async () => {
    try {
      const customFactors = await strategyBtApi.listCustomFactors();
      set({ customFactors });
    } catch (e) {
      console.warn('Failed to fetch custom factors:', e);
      set((s) => ({ warnings: [...s.warnings, '自定义因子加载失败'] }));
    }
  },

  fetchDatasets: async () => {
    try {
      const datasets = await strategyBtApi.listDatasets();
      set({ datasets });
    } catch (e) {
      console.warn('Failed to fetch datasets:', e);
      set((s) => ({ warnings: [...s.warnings, '数据集列表加载失败'] }));
    }
  },

  uploadDataset: async (file: File, name: string, freq = '1d', source = 'custom') => {
    set({ uploading: true, error: null });
    try {
      const res = await strategyBtApi.uploadDataset(file, name, freq, source);
      if (res.failedFiles && res.failedFiles.length > 0) {
        set(s => ({ warnings: [...s.warnings, `以下文件转换失败: ${res.failedFiles.join(', ')}`] }));
      }
      void get().fetchDatasets();
      set({ uploading: false });
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e), uploading: false });
      return false;
    }
  },

  createCustomFactor: async (name: string, expression: string, description = '') => {
    set({ error: null });
    try {
      await strategyBtApi.createCustomFactor(name, expression, description);
      void get().fetchFactors();
      void get().fetchCustomFactors();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  deleteCustomFactor: async (name: string) => {
    try {
      await strategyBtApi.deleteCustomFactor(name);
      void get().fetchFactors();
      void get().fetchCustomFactors();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  fetchCustomStrategies: async () => {
    try {
      const customStrategies = await strategyBtApi.listCustomStrategies();
      set({ customStrategies });
    } catch (e) {
      console.warn('Failed to fetch custom strategies:', e);
      set((s) => ({ warnings: [...s.warnings, '自定义策略加载失败'] }));
    }
  },

  createCustomStrategy: async (name: string, buyExpr: string, sellExpr: string, description = '') => {
    set({ error: null });
    try {
      await strategyBtApi.createCustomStrategy(name, buyExpr, sellExpr, description);
      void get().fetchStrategies();
      void get().fetchCustomStrategies();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  deleteCustomStrategy: async (name: string) => {
    try {
      await strategyBtApi.deleteCustomStrategy(name);
      void get().fetchStrategies();
      void get().fetchCustomStrategies();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  deleteRun: async (runId: number) => {
    try {
      await strategyBtApi.deleteRun(runId);
      void get().fetchRuns();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  deleteDataset: async (name: string) => {
    try {
      await strategyBtApi.deleteDataset(name);
      void get().fetchDatasets();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  fetchAvailableCodes: async (freq = '1d') => {
    try {
      const { codes } = await strategyBtApi.listAvailableCodes(freq);
      set({ availableCodes: codes });
    } catch (e) {
      console.warn('Failed to fetch available codes:', e);
      set((s) => ({ warnings: [...s.warnings, '可用代码加载失败'] }));
    }
  },

  clearCurrentRun: () => set({ currentRun: null }),
  clearWarnings: () => set({ warnings: [] }),

  pollRun: async (id: number) => {
    try {
      const run = await strategyBtApi.getRun(id);
      set({ currentRun: run });
      set((state) => ({
        runs: state.runs.map((r) => (r.id === id ? { ...r, ...run } : r)),
      }));
      return true;
    } catch (e) {
      console.warn('Poll failed for run', id, e);
      return false;
    }
  },

  initializeData: async () => {
    set({ initialLoading: true, warnings: [] });
    try {
      await Promise.all([
        get().fetchStrategies(),
        get().fetchFactors(),
        get().fetchCustomFactors(),
        get().fetchCustomStrategies(),
        get().fetchDatasets(),
        get().fetchRuns(),
      ]);
    } finally {
      set({ initialLoading: false });
    }
  },
}));

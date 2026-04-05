import { create } from 'zustand';
import { monitorApi } from '../api/monitor';
import type { MonitorTask, MonitorAlert, IndicatorsResponse } from '../api/monitor';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { USE_MOCK, MOCK_MONITOR_TASKS, MOCK_MONITOR_ALERTS, MOCK_INDICATORS } from '../mock/data';

interface MonitorState {
  tasks: MonitorTask[];
  alerts: MonitorAlert[];
  /** Flat indicator name list (backward compat) */
  indicators: string[];
  /** Rich indicator data with scenarios, templates, grouped items */
  indicatorData: IndicatorsResponse | null;
  loading: boolean;
  error: ParsedApiError | null;

  fetchTasks: () => Promise<void>;
  fetchAlerts: () => Promise<void>;
  fetchIndicators: () => Promise<void>;
  createTask: (data: Parameters<typeof monitorApi.create>[0]) => Promise<boolean>;
  updateTask: (taskId: number, data: Parameters<typeof monitorApi.update>[1]) => Promise<boolean>;
  deleteTask: (taskId: number) => Promise<boolean>;
  markAlertRead: (alertId: number) => Promise<void>;
}

export const useMonitorStore = create<MonitorState>((set, get) => ({
  tasks: [],
  alerts: [],
  indicators: [],
  indicatorData: null,
  loading: false,
  error: null,

  fetchTasks: async () => {
    if (USE_MOCK) {
      set({ tasks: [...MOCK_MONITOR_TASKS], loading: false });
      return;
    }
    set({ loading: true, error: null });
    try {
      const res = await monitorApi.list();
      set({ tasks: res.tasks, loading: false });
    } catch (e) {
      set({ error: getParsedApiError(e), loading: false });
    }
  },

  fetchAlerts: async () => {
    if (USE_MOCK) {
      set({ alerts: [...MOCK_MONITOR_ALERTS] });
      return;
    }
    try {
      const res = await monitorApi.getAlerts();
      set({ alerts: res.alerts });
    } catch (e) {
      set({ error: getParsedApiError(e) });
    }
  },

  fetchIndicators: async () => {
    if (USE_MOCK) {
      set({ indicators: [...MOCK_INDICATORS] });
      return;
    }
    try {
      const res = await monitorApi.getIndicators();
      // Flat list for backward compat
      const flat = Object.values(res.indicators).flat().map((item) => item.name);
      set({ indicators: flat, indicatorData: res });
    } catch (e) {
      // silent — indicators are optional
    }
  },

  createTask: async (data) => {
    if (USE_MOCK) {
      const newTask: MonitorTask = {
        id: Math.max(0, ...get().tasks.map((t) => t.id)) + 1,
        stockCode: data.stockCode,
        stockName: data.stockName || null,
        market: data.market || 'cn',
        conditions: data.conditions as MonitorTask['conditions'],
        isActive: true,
        intervalMinutes: data.intervalMinutes || 15,
        lastCheckedAt: null,
        lastTriggeredAt: null,
        createdAt: new Date().toISOString(),
      };
      set({ tasks: [...get().tasks, newTask] });
      return true;
    }
    try {
      await monitorApi.create(data);
      await get().fetchTasks();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  updateTask: async (taskId, data) => {
    if (USE_MOCK) {
      set({
        tasks: get().tasks.map((t) =>
          t.id === taskId
            ? { ...t, ...data, conditions: (data.conditions as MonitorTask['conditions']) ?? t.conditions }
            : t,
        ),
      });
      return true;
    }
    try {
      await monitorApi.update(taskId, data);
      await get().fetchTasks();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  deleteTask: async (taskId) => {
    if (USE_MOCK) {
      set({ tasks: get().tasks.filter((t) => t.id !== taskId) });
      return true;
    }
    try {
      await monitorApi.delete(taskId);
      await get().fetchTasks();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  markAlertRead: async (alertId) => {
    set({ alerts: get().alerts.map((a) => (a.id === alertId ? { ...a, isRead: true } : a)) });
    if (USE_MOCK) return;
    try {
      await monitorApi.markRead(alertId);
    } catch (e) {
      set({ error: getParsedApiError(e) });
    }
  },
}));

import { create } from 'zustand';
import { monitorApi } from '../api/monitor';
import type { MonitorTask, MonitorAlert } from '../api/monitor';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';

interface MonitorState {
  tasks: MonitorTask[];
  alerts: MonitorAlert[];
  indicators: string[];
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
  loading: false,
  error: null,

  fetchTasks: async () => {
    set({ loading: true, error: null });
    try {
      const res = await monitorApi.list();
      set({ tasks: res.tasks, loading: false });
    } catch (e) {
      set({ error: getParsedApiError(e), loading: false });
    }
  },

  fetchAlerts: async () => {
    try {
      const res = await monitorApi.getAlerts();
      set({ alerts: res.alerts });
    } catch (e) {
      set({ error: getParsedApiError(e) });
    }
  },

  fetchIndicators: async () => {
    try {
      const res = await monitorApi.getIndicators();
      set({ indicators: res.indicators });
    } catch (e) {
      // silent — indicators are optional
    }
  },

  createTask: async (data) => {
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
    try {
      await monitorApi.markRead(alertId);
      set({ alerts: get().alerts.map((a) => (a.id === alertId ? { ...a, isRead: true } : a)) });
    } catch (e) {
      set({ error: getParsedApiError(e) });
    }
  },
}));

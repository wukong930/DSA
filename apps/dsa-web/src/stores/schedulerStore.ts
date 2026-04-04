import { create } from 'zustand';
import { schedulerApi } from '../api/scheduler';
import type { ScheduledTask } from '../api/scheduler';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';

interface SchedulerState {
  tasks: ScheduledTask[];
  loading: boolean;
  error: ParsedApiError | null;

  fetchTasks: () => Promise<void>;
  createTask: (data: Parameters<typeof schedulerApi.create>[0]) => Promise<boolean>;
  updateTask: (taskId: number, data: Parameters<typeof schedulerApi.update>[1]) => Promise<boolean>;
  deleteTask: (taskId: number) => Promise<boolean>;
}

export const useSchedulerStore = create<SchedulerState>((set, get) => ({
  tasks: [],
  loading: false,
  error: null,

  fetchTasks: async () => {
    set({ loading: true, error: null });
    try {
      const res = await schedulerApi.list();
      set({ tasks: res.tasks, loading: false });
    } catch (e) {
      set({ error: getParsedApiError(e), loading: false });
    }
  },

  createTask: async (data) => {
    try {
      await schedulerApi.create(data);
      await get().fetchTasks();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  updateTask: async (taskId, data) => {
    try {
      await schedulerApi.update(taskId, data);
      await get().fetchTasks();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  deleteTask: async (taskId) => {
    try {
      await schedulerApi.delete(taskId);
      await get().fetchTasks();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },
}));

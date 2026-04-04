import { create } from 'zustand';
import { schedulerApi } from '../api/scheduler';
import type { ScheduledTask } from '../api/scheduler';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { USE_MOCK, MOCK_SCHEDULED_TASKS } from '../mock/data';

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
    if (USE_MOCK) {
      set({ tasks: [...MOCK_SCHEDULED_TASKS], loading: false });
      return;
    }
    set({ loading: true, error: null });
    try {
      const res = await schedulerApi.list();
      set({ tasks: res.tasks, loading: false });
    } catch (e) {
      set({ error: getParsedApiError(e), loading: false });
    }
  },

  createTask: async (data) => {
    if (USE_MOCK) {
      const newTask: ScheduledTask = {
        id: Math.max(0, ...get().tasks.map((t) => t.id)) + 1,
        userId: 0,
        taskType: data.taskType,
        stockCodes: data.stockCodes,
        scheduleConfig: data.scheduleConfig,
        isActive: true,
        lastRunAt: null,
        nextRunAt: new Date(Date.now() + 86400000).toISOString(),
        createdAt: new Date().toISOString(),
      };
      set({ tasks: [...get().tasks, newTask] });
      return true;
    }
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
    if (USE_MOCK) {
      set({
        tasks: get().tasks.map((t) =>
          t.id === taskId
            ? {
                ...t,
                isActive: data.isActive ?? t.isActive,
                stockCodes: data.stockCodes ?? t.stockCodes,
                scheduleConfig: data.scheduleConfig ?? t.scheduleConfig,
              }
            : t,
        ),
      });
      return true;
    }
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
    if (USE_MOCK) {
      set({ tasks: get().tasks.filter((t) => t.id !== taskId) });
      return true;
    }
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

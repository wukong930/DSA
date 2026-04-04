import apiClient from './index';
import { toCamelCase } from './utils';

export interface ScheduledTask {
  id: number;
  userId: number;
  taskType: string;
  stockCodes: string[];
  scheduleConfig: Record<string, unknown>;
  isActive: boolean;
  lastRunAt: string | null;
  nextRunAt: string | null;
  createdAt: string | null;
}

export const schedulerApi = {
  list: async (): Promise<{ tasks: ScheduledTask[]; total: number }> => {
    const res = await apiClient.get<Record<string, unknown>>('/api/v1/scheduler');
    return toCamelCase(res.data);
  },

  create: async (data: {
    taskType: string;
    stockCodes: string[];
    scheduleConfig: Record<string, unknown>;
  }): Promise<{ id: number; message: string }> => {
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/scheduler', {
      task_type: data.taskType,
      stock_codes: data.stockCodes,
      schedule_config: data.scheduleConfig,
    });
    return toCamelCase(res.data);
  },

  update: async (
    taskId: number,
    data: { isActive?: boolean; stockCodes?: string[]; scheduleConfig?: Record<string, unknown> },
  ): Promise<{ message: string }> => {
    const res = await apiClient.put<Record<string, unknown>>(`/api/v1/scheduler/${taskId}`, {
      is_active: data.isActive,
      stock_codes: data.stockCodes,
      schedule_config: data.scheduleConfig,
    });
    return toCamelCase(res.data);
  },

  delete: async (taskId: number): Promise<{ message: string }> => {
    const res = await apiClient.delete<Record<string, unknown>>(`/api/v1/scheduler/${taskId}`);
    return toCamelCase(res.data);
  },
};

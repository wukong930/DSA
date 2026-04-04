import apiClient from './index';
import { toCamelCase } from './utils';

export interface MonitorTask {
  id: number;
  stockCode: string;
  stockName: string | null;
  market: string;
  conditions: Array<{ indicator: string; op: string; value?: number; indicator2?: string }>;
  isActive: boolean;
  intervalMinutes: number;
  lastCheckedAt: string | null;
  lastTriggeredAt: string | null;
  createdAt: string | null;
}

export interface MonitorAlert {
  id: number;
  taskId: number;
  stockCode: string;
  conditionMatched: Record<string, unknown>;
  indicatorValues: Record<string, number>;
  isRead: boolean;
  notifiedVia: string | null;
  createdAt: string | null;
}

export const monitorApi = {
  list: async (): Promise<{ tasks: MonitorTask[]; total: number }> => {
    const res = await apiClient.get<Record<string, unknown>>('/api/v1/monitor');
    return toCamelCase(res.data);
  },

  create: async (data: {
    stockCode: string;
    stockName?: string;
    market?: string;
    conditions: Array<Record<string, unknown>>;
    intervalMinutes?: number;
  }): Promise<{ id: number; message: string }> => {
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/monitor', {
      stock_code: data.stockCode,
      stock_name: data.stockName,
      market: data.market || 'cn',
      conditions: data.conditions,
      interval_minutes: data.intervalMinutes || 15,
    });
    return toCamelCase(res.data);
  },

  update: async (
    taskId: number,
    data: { isActive?: boolean; conditions?: Array<Record<string, unknown>>; intervalMinutes?: number },
  ): Promise<{ message: string }> => {
    const res = await apiClient.put<Record<string, unknown>>(`/api/v1/monitor/${taskId}`, {
      is_active: data.isActive,
      conditions: data.conditions,
      interval_minutes: data.intervalMinutes,
    });
    return toCamelCase(res.data);
  },

  delete: async (taskId: number): Promise<{ message: string }> => {
    const res = await apiClient.delete<Record<string, unknown>>(`/api/v1/monitor/${taskId}`);
    return toCamelCase(res.data);
  },

  getAlerts: async (): Promise<{ alerts: MonitorAlert[]; total: number }> => {
    const res = await apiClient.get<Record<string, unknown>>('/api/v1/monitor/alerts');
    return toCamelCase(res.data);
  },

  markRead: async (alertId: number): Promise<{ message: string }> => {
    const res = await apiClient.post<Record<string, unknown>>(`/api/v1/monitor/alerts/${alertId}/read`);
    return toCamelCase(res.data);
  },

  getIndicators: async (): Promise<{ indicators: string[] }> => {
    const res = await apiClient.get<Record<string, Array<{ name: string }>>>('/api/v1/monitor/indicators');
    const indicators = Object.values(res.data).flat().map((item) => item.name);
    return { indicators };
  },
};

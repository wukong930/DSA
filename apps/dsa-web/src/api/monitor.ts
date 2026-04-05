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

export interface IndicatorItem {
  name: string;
  cnName: string;
  cnDesc: string;
  description: string;
  category: string;
}

export interface PresetTemplate {
  key: string;
  name: string;
  description: string;
  conditions: Array<{ indicator: string; op: string; value?: number; indicator2?: string }>;
}

export interface IndicatorsResponse {
  indicators: Record<string, IndicatorItem[]>;
  templates: PresetTemplate[];
  scenarios: Record<string, string>;
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

  getIndicators: async (): Promise<IndicatorsResponse> => {
    const res = await apiClient.get<Record<string, unknown>>('/api/v1/monitor/indicators');
    const data = res.data as Record<string, unknown>;
    // Rich response with scenarios, templates, and grouped indicators
    const rawIndicators = (data.indicators ?? data.flat ?? {}) as Record<string, Array<Record<string, string>>>;
    const indicators: Record<string, IndicatorItem[]> = {};
    for (const [group, items] of Object.entries(rawIndicators)) {
      indicators[group] = (items || []).map((item) => ({
        name: item.name,
        cnName: item.cn_name || item.name,
        cnDesc: item.cn_desc || item.description || '',
        description: item.description || '',
        category: item.category || group,
      }));
    }
    const templates = ((data.templates ?? []) as Array<Record<string, unknown>>).map((t) => ({
      key: t.key as string,
      name: t.name as string,
      description: t.description as string,
      conditions: t.conditions as PresetTemplate['conditions'],
    }));
    const scenarios = (data.scenarios ?? {}) as Record<string, string>;
    return { indicators, templates, scenarios };
  },
};

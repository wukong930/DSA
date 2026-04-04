import apiClient from './index';
import { toCamelCase } from './utils';

export interface WatchlistItem {
  id: number;
  userId: number;
  stockCode: string;
  stockName: string | null;
  market: string;
  tags: string[];
  notes: string | null;
  addedAt: string | null;
}

export interface FilterSignal {
  indicator: string;
  op: string;
  value: number;
  actualValue: number;
  triggered: boolean;
}

export interface FilterResult {
  stockCode: string;
  stockName: string | null;
  signals: FilterSignal[];
  indicatorSnapshot: Record<string, number>;
}

export const watchlistApi = {
  list: async (): Promise<{ items: WatchlistItem[]; total: number }> => {
    const res = await apiClient.get<Record<string, unknown>>('/api/v1/watchlist');
    return toCamelCase(res.data);
  },

  add: async (data: {
    stockCode: string;
    stockName?: string;
    market?: string;
    tags?: string[];
    notes?: string;
  }): Promise<{ id: number; message: string }> => {
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/watchlist', {
      stock_code: data.stockCode,
      stock_name: data.stockName,
      market: data.market || 'cn',
      tags: data.tags,
      notes: data.notes,
    });
    return toCamelCase(res.data);
  },

  update: async (
    itemId: number,
    data: { tags?: string[]; notes?: string },
  ): Promise<{ message: string }> => {
    const res = await apiClient.put<Record<string, unknown>>(`/api/v1/watchlist/${itemId}`, {
      tags: data.tags,
      notes: data.notes,
    });
    return toCamelCase(res.data);
  },

  remove: async (itemId: number): Promise<{ message: string }> => {
    const res = await apiClient.delete<Record<string, unknown>>(`/api/v1/watchlist/${itemId}`);
    return toCamelCase(res.data);
  },

  filter: async (conditions: Array<Record<string, unknown>>): Promise<{ results: FilterResult[]; matched: number }> => {
    const res = await apiClient.post<Record<string, unknown>>('/api/v1/watchlist/filter', {
      conditions,
    });
    return toCamelCase(res.data);
  },
};

import { create } from 'zustand';
import { watchlistApi } from '../api/watchlist';
import type { WatchlistItem, FilterResult } from '../api/watchlist';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { USE_MOCK, MOCK_WATCHLIST_ITEMS, MOCK_FILTER_RESULTS } from '../mock/data';

interface WatchlistState {
  items: WatchlistItem[];
  filterResults: FilterResult[];
  loading: boolean;
  filtering: boolean;
  error: ParsedApiError | null;

  fetchItems: () => Promise<void>;
  addItem: (data: Parameters<typeof watchlistApi.add>[0]) => Promise<boolean>;
  removeItem: (itemId: number) => Promise<boolean>;
  updateItem: (itemId: number, data: Parameters<typeof watchlistApi.update>[1]) => Promise<boolean>;
  filterWatchlist: (conditions: Array<Record<string, unknown>>) => Promise<void>;
  clearFilter: () => void;
}

export const useWatchlistStore = create<WatchlistState>((set, get) => ({
  items: [],
  filterResults: [],
  loading: false,
  filtering: false,
  error: null,

  fetchItems: async () => {
    if (USE_MOCK) {
      set({ items: [...MOCK_WATCHLIST_ITEMS], loading: false });
      return;
    }
    set({ loading: true, error: null });
    try {
      const res = await watchlistApi.list();
      set({ items: res.items, loading: false });
    } catch (e) {
      set({ error: getParsedApiError(e), loading: false });
    }
  },

  addItem: async (data) => {
    if (USE_MOCK) {
      const newItem: WatchlistItem = {
        id: Math.max(0, ...get().items.map((i) => i.id)) + 1,
        userId: 0,
        stockCode: data.stockCode,
        stockName: data.stockName || null,
        market: data.market || 'cn',
        tags: data.tags || [],
        notes: data.notes || null,
        addedAt: new Date().toISOString(),
      };
      set({ items: [...get().items, newItem] });
      return true;
    }
    try {
      await watchlistApi.add(data);
      await get().fetchItems();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  removeItem: async (itemId) => {
    if (USE_MOCK) {
      set({ items: get().items.filter((i) => i.id !== itemId) });
      return true;
    }
    try {
      await watchlistApi.remove(itemId);
      await get().fetchItems();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  updateItem: async (itemId, data) => {
    if (USE_MOCK) {
      set({
        items: get().items.map((i) =>
          i.id === itemId ? { ...i, tags: data.tags ?? i.tags, notes: data.notes ?? i.notes } : i,
        ),
      });
      return true;
    }
    try {
      await watchlistApi.update(itemId, data);
      await get().fetchItems();
      return true;
    } catch (e) {
      set({ error: getParsedApiError(e) });
      return false;
    }
  },

  filterWatchlist: async (conditions) => {
    if (USE_MOCK) {
      set({ filtering: true });
      await new Promise((r) => setTimeout(r, 500));
      set({ filterResults: [...MOCK_FILTER_RESULTS], filtering: false });
      return;
    }
    set({ filtering: true, error: null });
    try {
      const res = await watchlistApi.filter(conditions);
      set({ filterResults: res.results, filtering: false });
    } catch (e) {
      set({ error: getParsedApiError(e), filtering: false });
    }
  },

  clearFilter: () => set({ filterResults: [] }),
}));

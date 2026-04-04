import { create } from 'zustand';
import { watchlistApi } from '../api/watchlist';
import type { WatchlistItem, FilterResult } from '../api/watchlist';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';

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
    set({ loading: true, error: null });
    try {
      const res = await watchlistApi.list();
      set({ items: res.items, loading: false });
    } catch (e) {
      set({ error: getParsedApiError(e), loading: false });
    }
  },

  addItem: async (data) => {
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

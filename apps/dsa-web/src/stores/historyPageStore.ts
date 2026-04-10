import { create } from 'zustand';
import type { ParsedApiError } from '../api/error';
import { getParsedApiError } from '../api/error';
import { historyApi } from '../api/history';
import type { AnalysisReport, HistoryItem, HistoryListResponse, HistoryGroupItem } from '../types/analysis';
import { USE_MOCK, MOCK_HISTORY_ITEMS, MOCK_REPORT_MAOTAI, MOCK_HISTORY_GROUPS, MOCK_REPORTS_MAP } from '../mock/data';

const PAGE_SIZE = 20;

let reportRequestSeq = 0;
let historyRequestSeq = 0;

export interface HistoryPageState {
  filterStockCode: string;
  historyItems: HistoryItem[];
  isLoadingHistory: boolean;
  isLoadingMore: boolean;
  hasMore: boolean;
  currentPage: number;
  error: ParsedApiError | null;
  selectedHistoryIds: number[];
  isDeletingHistory: boolean;
  selectedReport: AnalysisReport | null;
  isLoadingReport: boolean;
  markdownDrawerOpen: boolean;

  // Grouped view state
  groups: HistoryGroupItem[];
  expandedGroups: Set<string>;
  groupSubItems: Record<string, HistoryItem[]>;
  isLoadingGroups: boolean;
  isLoadingGroupItems: Record<string, boolean>;

  setFilterStockCode: (code: string) => void;
  loadInitialHistory: () => Promise<void>;
  loadMoreHistory: () => Promise<void>;
  selectHistoryItem: (recordId: number) => Promise<void>;
  toggleHistorySelection: (recordId: number) => void;
  toggleSelectAllVisible: () => void;
  deleteSelectedHistory: () => Promise<void>;
  openMarkdownDrawer: () => void;
  closeMarkdownDrawer: () => void;
  clearError: () => void;

  // Grouped view actions
  loadGroups: () => Promise<void>;
  toggleGroup: (stockCode: string) => Promise<void>;
}

async function fetchHistory(
  get: () => HistoryPageState,
  set: (partial: Partial<HistoryPageState>) => void,
  options: { reset?: boolean; autoSelectFirst?: boolean } = {},
): Promise<HistoryListResponse | null> {
  const { reset = true, autoSelectFirst = false } = options;
  const state = get();
  const page = reset ? 1 : state.currentPage + 1;
  const requestId = ++historyRequestSeq;

  set(
    reset
      ? { isLoadingHistory: true, isLoadingMore: false, currentPage: 1 }
      : { isLoadingMore: true },
  );

  try {
    const params: Record<string, unknown> = { page, limit: PAGE_SIZE };
    const code = state.filterStockCode.trim();
    if (code) params.stockCode = code;

    const response = await historyApi.getList(params as Parameters<typeof historyApi.getList>[0]);
    if (requestId !== historyRequestSeq) return null;

    if (reset) {
      set({ historyItems: response.items, currentPage: 1 });
    } else {
      set({
        historyItems: [...get().historyItems, ...response.items],
        currentPage: page,
      });
    }

    const totalLoaded = reset ? response.items.length : get().historyItems.length;
    set({ hasMore: totalLoaded < response.total });

    const visibleIds = new Set(get().historyItems.map((item) => item.id));
    set({
      selectedHistoryIds: get().selectedHistoryIds.filter((id) => visibleIds.has(id)),
    });

    if (autoSelectFirst && response.items.length > 0 && !get().selectedReport) {
      await get().selectHistoryItem(response.items[0].id);
    }

    return response;
  } catch (error) {
    if (requestId !== historyRequestSeq) return null;
    set({ error: getParsedApiError(error) });
    return null;
  } finally {
    if (requestId === historyRequestSeq) {
      set({ isLoadingHistory: false, isLoadingMore: false });
    }
  }
}

export const useHistoryPageStore = create<HistoryPageState>((set, get) => ({
  filterStockCode: '',
  historyItems: [],
  isLoadingHistory: false,
  isLoadingMore: false,
  hasMore: true,
  currentPage: 1,
  error: null,
  selectedHistoryIds: [],
  isDeletingHistory: false,
  selectedReport: null,
  isLoadingReport: false,
  markdownDrawerOpen: false,

  // Grouped view state
  groups: [],
  expandedGroups: new Set<string>(),
  groupSubItems: {},
  isLoadingGroups: false,
  isLoadingGroupItems: {},

  setFilterStockCode: (code) => {
    set({ filterStockCode: code });
    void get().loadGroups();
  },

  loadInitialHistory: async () => {
    if (USE_MOCK) {
      await get().loadGroups();
      return;
    }
    await get().loadGroups();
  },

  loadMoreHistory: async () => {
    if (USE_MOCK) return;
    const state = get();
    if (state.isLoadingMore || !state.hasMore) return;
    await fetchHistory(get, set, { reset: false });
  },

  selectHistoryItem: async (recordId) => {
    if (USE_MOCK) {
      const item = MOCK_HISTORY_ITEMS.find((h) => h.id === recordId);
      const report = item ? MOCK_REPORTS_MAP[item.stockCode] : MOCK_REPORT_MAOTAI;
      if (report && item) {
        set({ selectedReport: { ...report, meta: { ...report.meta, id: item.id, queryId: item.queryId, createdAt: item.createdAt } }, isLoadingReport: false });
      } else {
        set({ selectedReport: MOCK_REPORT_MAOTAI, isLoadingReport: false });
      }
      return;
    }
    const requestId = ++reportRequestSeq;
    const shouldShowInitialLoading = !get().selectedReport;
    if (shouldShowInitialLoading) {
      set({ isLoadingReport: true });
    }

    try {
      const report = await historyApi.getDetail(recordId);
      if (requestId !== reportRequestSeq) return;
      set({ selectedReport: report, error: null, isLoadingReport: false });
    } catch (error) {
      if (requestId !== reportRequestSeq) return;
      set({ error: getParsedApiError(error), isLoadingReport: false });
    }
  },

  toggleHistorySelection: (recordId) => {
    const selected = new Set(get().selectedHistoryIds);
    if (selected.has(recordId)) {
      selected.delete(recordId);
    } else {
      selected.add(recordId);
    }
    set({ selectedHistoryIds: Array.from(selected) });
  },

  toggleSelectAllVisible: () => {
    const visibleIds = get().historyItems.map((item) => item.id);
    const selectedIds = get().selectedHistoryIds;
    const visibleSet = new Set(visibleIds);
    const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id));

    set({
      selectedHistoryIds: allSelected
        ? selectedIds.filter((id) => !visibleSet.has(id))
        : Array.from(new Set([...selectedIds, ...visibleIds])),
    });
  },

  deleteSelectedHistory: async () => {
    if (USE_MOCK) {
      const deletedIds = new Set(get().selectedHistoryIds);
      set({
        historyItems: get().historyItems.filter((i) => !deletedIds.has(i.id)),
        selectedHistoryIds: [],
        isDeletingHistory: false,
      });
      return;
    }
    const state = get();
    const recordIds = Array.from(new Set(state.selectedHistoryIds));
    if (recordIds.length === 0 || state.isDeletingHistory) return;

    set({ isDeletingHistory: true });
    try {
      await historyApi.deleteRecords(recordIds);

      const deletedIds = new Set(recordIds);
      const selectedWasDeleted =
        state.selectedReport?.meta.id !== undefined && deletedIds.has(state.selectedReport.meta.id);

      set({ selectedHistoryIds: [] });

      // Reload groups after deletion
      await get().loadGroups();

      if (selectedWasDeleted) {
        const groups = get().groups;
        if (groups.length > 0) {
          await get().selectHistoryItem(groups[0].latestId);
        } else {
          set({ selectedReport: null });
        }
      }
    } catch (error) {
      set({ error: getParsedApiError(error) });
    } finally {
      set({ isDeletingHistory: false });
    }
  },

  openMarkdownDrawer: () => set({ markdownDrawerOpen: true }),
  closeMarkdownDrawer: () => set({ markdownDrawerOpen: false }),
  clearError: () => set({ error: null }),

  // Grouped view actions
  loadGroups: async () => {
    if (USE_MOCK) {
      const code = get().filterStockCode.trim();
      const groups = code
        ? MOCK_HISTORY_GROUPS.filter((g) => g.stockCode.includes(code))
        : [...MOCK_HISTORY_GROUPS];
      set({ groups, groupSubItems: {}, expandedGroups: new Set<string>(), isLoadingGroups: false });
      if (groups.length > 0 && !get().selectedReport) {
        await get().selectHistoryItem(groups[0].latestId);
      }
      return;
    }
    set({ isLoadingGroups: true });
    try {
      const code = get().filterStockCode.trim();
      const response = await historyApi.getGrouped(code || undefined);
      set({
        groups: response.groups,
        groupSubItems: {},
        expandedGroups: new Set<string>(),
      });

      // Auto-select first group's latest report
      if (response.groups.length > 0 && !get().selectedReport) {
        await get().selectHistoryItem(response.groups[0].latestId);
      }
    } catch (error) {
      set({ error: getParsedApiError(error) });
    } finally {
      set({ isLoadingGroups: false });
    }
  },

  toggleGroup: async (stockCode: string) => {
    const expanded = new Set(get().expandedGroups);

    if (expanded.has(stockCode)) {
      expanded.delete(stockCode);
      set({ expandedGroups: expanded });
      return;
    }

    expanded.add(stockCode);
    set({ expandedGroups: expanded });

    // Load sub-items if not cached
    if (!get().groupSubItems[stockCode]) {
      if (USE_MOCK) {
        const items = MOCK_HISTORY_ITEMS.filter((h) => h.stockCode === stockCode);
        set({ groupSubItems: { ...get().groupSubItems, [stockCode]: items } });
        return;
      }
      set({
        isLoadingGroupItems: { ...get().isLoadingGroupItems, [stockCode]: true },
      });
      try {
        const response = await historyApi.getList({ stockCode, page: 1, limit: 100 });
        set({
          groupSubItems: { ...get().groupSubItems, [stockCode]: response.items },
        });
      } catch (error) {
        set({ error: getParsedApiError(error) });
      } finally {
        set({
          isLoadingGroupItems: { ...get().isLoadingGroupItems, [stockCode]: false },
        });
      }
    }
  },
}));

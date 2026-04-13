import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { ApiErrorAlert, Button, ConfirmDialog, EmptyState } from '../components/common';
import { DashboardStateBlock } from '../components/dashboard';
import { HistoryGroupList } from '../components/history';
import { ReportMarkdown, ReportSummary } from '../components/report';
import { useHistoryPageStore } from '../stores/historyPageStore';
import { normalizeReportLanguage, getReportText } from '../utils/reportLanguage';

const HistoryPage: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false);
  const [filterInput, setFilterInput] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const {
    error,
    groups,
    selectedHistoryIds,
    isDeletingHistory,
    selectedReport,
    isLoadingReport,
    markdownDrawerOpen,
    loadInitialHistory,
    deleteSelectedHistory,
    deleteAllHistory,
    setFilterStockCode,
    openMarkdownDrawer,
    closeMarkdownDrawer,
    clearError,
  } = useHistoryPageStore(
    useShallow((state) => ({
      error: state.error,
      groups: state.groups,
      selectedHistoryIds: state.selectedHistoryIds,
      isDeletingHistory: state.isDeletingHistory,
      selectedReport: state.selectedReport,
      isLoadingReport: state.isLoadingReport,
      markdownDrawerOpen: state.markdownDrawerOpen,
      loadInitialHistory: state.loadInitialHistory,
      deleteSelectedHistory: state.deleteSelectedHistory,
      deleteAllHistory: state.deleteAllHistory,
      setFilterStockCode: state.setFilterStockCode,
      openMarkdownDrawer: state.openMarkdownDrawer,
      closeMarkdownDrawer: state.closeMarkdownDrawer,
      clearError: state.clearError,
    })),
  );

  useEffect(() => {
    document.title = '历史报告 - DSA';
    void loadInitialHistory();
  }, [loadInitialHistory]);

  const handleFilterChange = useCallback(
    (value: string) => {
      setFilterInput(value);
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        setFilterStockCode(value.trim());
      }, 300);
    },
    [setFilterStockCode],
  );

  const handleDeleteSelected = useCallback(() => {
    void deleteSelectedHistory();
    setShowDeleteConfirm(false);
  }, [deleteSelectedHistory]);

  const handleDeleteAll = useCallback(() => {
    void deleteAllHistory();
    setShowDeleteAllConfirm(false);
  }, [deleteAllHistory]);

  const reportLanguage = normalizeReportLanguage(selectedReport?.meta.reportLanguage);
  const reportText = getReportText(reportLanguage);

  const sidebarContent = (
    <div className="flex min-h-0 h-full flex-col gap-3 overflow-hidden">
      <div className="relative flex-shrink-0">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-text" />
        <input
          type="text"
          value={filterInput}
          onChange={(e) => handleFilterChange(e.target.value)}
          placeholder="按股票代码筛选..."
          className="input-surface input-focus-glow h-10 w-full rounded-xl border bg-transparent pl-9 pr-3 text-sm transition-all focus:outline-none"
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        <HistoryGroupList />
      </div>
      {selectedHistoryIds.length > 0 && (
        <div className="flex items-center justify-between px-3 py-2 border-t border-subtle-hover">
          <span className="text-xs text-muted-text">已选 {selectedHistoryIds.length} 条</span>
          <Button
            size="sm"
            variant="danger"
            onClick={() => setShowDeleteConfirm(true)}
            disabled={isDeletingHistory}
          >
            删除
          </Button>
        </div>
      )}
      {selectedHistoryIds.length === 0 && groups.length > 0 && (
        <div className="flex items-center justify-end px-3 py-2 border-t border-subtle-hover">
          <Button
            size="sm"
            variant="danger"
            onClick={() => setShowDeleteAllConfirm(true)}
            disabled={isDeletingHistory}
          >
            删除全部
          </Button>
        </div>
      )}
    </div>
  );

  return (
    <div
      className="flex h-[calc(100vh-5rem)] w-full flex-col overflow-hidden md:flex-row sm:h-[calc(100vh-5.5rem)] lg:h-[calc(100vh-2rem)]"
    >
      <div className="flex-1 flex flex-col min-h-0 min-w-0 max-w-full lg:max-w-6xl mx-auto w-full">
        <header className="flex min-w-0 flex-shrink-0 items-center px-3 py-3 md:px-4 md:py-4">
          <div className="flex min-w-0 flex-1 items-center gap-2.5">
            <button
              onClick={() => setSidebarOpen(true)}
              className="md:hidden -ml-1 flex-shrink-0 rounded-lg p-1.5 text-secondary-text transition-colors hover:bg-hover hover:text-foreground"
              aria-label="历史列表"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-lg font-semibold text-foreground">历史报告</h1>
            <span className="text-sm text-muted-text">浏览所有分析历史报告</span>
          </div>
        </header>

        <div className="flex-1 flex min-h-0 overflow-hidden">
          <div className="hidden min-h-0 w-64 shrink-0 flex-col overflow-hidden pl-4 pb-4 md:flex lg:w-72">
            {sidebarContent}
          </div>

          {sidebarOpen ? (
            <div className="fixed inset-0 z-40 md:hidden" onClick={() => setSidebarOpen(false)}>
              <div className="page-drawer-overlay absolute inset-0" />
              <div
                className="dashboard-card absolute bottom-0 left-0 top-0 flex w-72 flex-col overflow-hidden !rounded-none !rounded-r-xl p-3 shadow-2xl"
                onClick={(event) => event.stopPropagation()}
              >
                {sidebarContent}
              </div>
            </div>
          ) : null}

          <section className="flex-1 min-w-0 min-h-0 overflow-x-auto overflow-y-auto px-3 pb-4 md:px-6 touch-pan-y">
            {error ? (
              <ApiErrorAlert error={error} className="mb-3" onDismiss={clearError} />
            ) : null}
            {isLoadingReport ? (
              <div className="flex h-full flex-col items-center justify-center">
                <DashboardStateBlock title="加载报告中..." loading />
              </div>
            ) : selectedReport ? (
              <div className="max-w-4xl space-y-4 pb-8">
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <Button
                    variant="home-action-ai"
                    size="sm"
                    disabled={selectedReport.meta.id === undefined}
                    onClick={openMarkdownDrawer}
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    {reportText.fullReport}
                  </Button>
                </div>
                <ReportSummary data={selectedReport} isHistory />
              </div>
            ) : (
              <div className="flex h-full items-center justify-center">
                <EmptyState
                  title="选择报告查看"
                  description="从左侧列表选择一条历史分析报告，或使用搜索框按股票代码筛选。"
                  className="max-w-xl border-dashed"
                  icon={(
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  )}
                />
              </div>
            )}
          </section>
        </div>
      </div>

      {markdownDrawerOpen && selectedReport?.meta.id ? (
        <ReportMarkdown
          recordId={selectedReport.meta.id}
          stockName={selectedReport.meta.stockName || ''}
          stockCode={selectedReport.meta.stockCode}
          reportLanguage={reportLanguage}
          onClose={closeMarkdownDrawer}
        />
      ) : null}

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="删除历史记录"
        message={
          selectedHistoryIds.length === 1
            ? '确认删除这条历史记录吗？删除后将不可恢复。'
            : `确认删除选中的 ${selectedHistoryIds.length} 条历史记录吗？删除后将不可恢复。`
        }
        confirmText={isDeletingHistory ? '删除中...' : '确认删除'}
        cancelText="取消"
        isDanger
        onConfirm={handleDeleteSelected}
        onCancel={() => setShowDeleteConfirm(false)}
      />

      <ConfirmDialog
        isOpen={showDeleteAllConfirm}
        title="删除全部历史记录"
        message="确认删除所有历史分析记录吗？此操作不可恢复。"
        confirmText={isDeletingHistory ? '删除中...' : '确认删除全部'}
        cancelText="取消"
        isDanger
        onConfirm={handleDeleteAll}
        onCancel={() => setShowDeleteAllConfirm(false)}
      />
    </div>
  );
};

export default HistoryPage;
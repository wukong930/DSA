import type React from 'react';
import { useShallow } from 'zustand/react/shallow';
import { Loader2 } from 'lucide-react';
import { EmptyState } from '../common';
import { HistoryGroupHeader } from './HistoryGroupHeader';
import { HistoryListItem } from './HistoryListItem';
import { useHistoryPageStore } from '../../stores/historyPageStore';

export const HistoryGroupList: React.FC = () => {
  const {
    groups,
    expandedGroups,
    groupSubItems,
    isLoadingGroups,
    isLoadingGroupItems,
    selectedReport,
    selectedHistoryIds,
    isDeletingHistory,
    toggleGroup,
    selectHistoryItem,
    toggleHistorySelection,
  } = useHistoryPageStore(
    useShallow((state) => ({
      groups: state.groups,
      expandedGroups: state.expandedGroups,
      groupSubItems: state.groupSubItems,
      isLoadingGroups: state.isLoadingGroups,
      isLoadingGroupItems: state.isLoadingGroupItems,
      selectedReport: state.selectedReport,
      selectedHistoryIds: state.selectedHistoryIds,
      isDeletingHistory: state.isDeletingHistory,
      toggleGroup: state.toggleGroup,
      selectHistoryItem: state.selectHistoryItem,
      toggleHistorySelection: state.toggleHistorySelection,
    })),
  );

  if (isLoadingGroups) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-5 w-5 animate-spin text-muted-text" />
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <EmptyState
        title="暂无历史记录"
        description="运行分析后，历史报告将在这里显示"
        icon={
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
      />
    );
  }

  const currentViewingId = selectedReport?.meta.id;

  return (
    <div className="space-y-0.5">
      {groups.map((group) => {
        const isExpanded = expandedGroups.has(group.stockCode);
        const subItems = groupSubItems[group.stockCode];
        const isLoadingSub = isLoadingGroupItems[group.stockCode];

        return (
          <div key={group.stockCode}>
            <HistoryGroupHeader
              group={group}
              isExpanded={isExpanded}
              onToggle={() => toggleGroup(group.stockCode)}
            />

            {isExpanded && (
              <div className="ml-6 pl-2 border-l border-subtle-hover/50 space-y-0.5">
                {isLoadingSub ? (
                  <div className="flex items-center gap-2 py-3 px-2 text-muted-text text-xs">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    加载中...
                  </div>
                ) : subItems && subItems.length > 0 ? (
                  subItems.map((item) => (
                    <HistoryListItem
                      key={item.id}
                      item={item}
                      isViewing={item.id === currentViewingId}
                      isChecked={selectedHistoryIds.includes(item.id)}
                      isDeleting={isDeletingHistory}
                      onToggleChecked={toggleHistorySelection}
                      onClick={selectHistoryItem}
                    />
                  ))
                ) : null}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

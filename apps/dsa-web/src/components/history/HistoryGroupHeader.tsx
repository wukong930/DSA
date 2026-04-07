import type React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Badge } from '../common';
import type { HistoryGroupItem } from '../../types/analysis';
import { getSentimentColor } from '../../types/analysis';
import { formatDateTime } from '../../utils/format';
import { truncateStockName, isStockNameTruncated } from '../../utils/stockName';

interface HistoryGroupHeaderProps {
  group: HistoryGroupItem;
  isExpanded: boolean;
  onToggle: () => void;
}

const getOperationBadgeLabel = (advice?: string) => {
  const normalized = advice?.trim();
  if (!normalized) return '情绪';
  if (normalized.includes('减仓')) return '减仓';
  if (normalized.includes('卖')) return '卖出';
  if (normalized.includes('观望') || normalized.includes('等待')) return '观望';
  if (normalized.includes('买') || normalized.includes('布局')) return '买入';
  return normalized.split(/[，。；、\s]/)[0] || '建议';
};

export const HistoryGroupHeader: React.FC<HistoryGroupHeaderProps> = ({
  group,
  isExpanded,
  onToggle,
}) => {
  const sentimentColor =
    group.latestSentimentScore !== undefined
      ? getSentimentColor(group.latestSentimentScore)
      : null;
  const stockName = group.stockName || group.stockCode;
  const isTruncated = isStockNameTruncated(stockName);

  return (
    <button
      type="button"
      onClick={onToggle}
      className="w-full text-left p-2.5 rounded-lg hover:bg-subtle-hover/50 transition-colors duration-150 group/header"
    >
      <div className="flex items-center gap-2">
        <span className="text-muted-text flex-shrink-0 w-4">
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </span>

        {sentimentColor && (
          <div
            className="w-1 h-8 rounded-full flex-shrink-0"
            style={{
              backgroundColor: sentimentColor,
              boxShadow: `0 0 10px ${sentimentColor}40`,
            }}
          />
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <span className={`text-sm font-semibold text-foreground tracking-tight${isTruncated ? '' : ''}`}>
                <span className="group-hover/header:hidden">
                  {truncateStockName(stockName)}
                </span>
                <span className="hidden group-hover/header:inline">
                  {stockName}
                </span>
              </span>
              <span className="ml-1.5 text-[11px] text-muted-text bg-subtle-hover/60 px-1.5 py-0.5 rounded-full">
                {group.recordCount}条
              </span>
            </div>

            {sentimentColor && (
              <Badge
                variant="default"
                size="sm"
                className="shrink-0 shadow-none text-[11px] font-semibold leading-none"
                style={{
                  color: sentimentColor,
                  borderColor: `${sentimentColor}30`,
                  backgroundColor: `${sentimentColor}10`,
                }}
              >
                {getOperationBadgeLabel(group.latestOperationAdvice)} {group.latestSentimentScore}
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] text-secondary-text font-mono">
              {group.stockCode}
            </span>
            {group.latestCreatedAt && (
              <>
                <span className="w-1 h-1 rounded-full bg-subtle-hover" />
                <span className="text-[11px] text-muted-text">
                  {formatDateTime(group.latestCreatedAt)}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </button>
  );
};

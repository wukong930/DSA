import React from 'react';
import { TrendingDown, TrendingUp, Minus } from 'lucide-react';
import type { ForecastData } from '../../api/forecast';

interface ForecastPanelProps {
  forecast: ForecastData;
}

const TREND_CONFIG = {
  up: { icon: TrendingUp, label: '看涨', color: 'text-green-500', bg: 'bg-green-500/10' },
  down: { icon: TrendingDown, label: '看跌', color: 'text-red-500', bg: 'bg-red-500/10' },
  neutral: { icon: Minus, label: '震荡', color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
} as const;

export const ForecastPanel: React.FC<ForecastPanelProps> = ({ forecast }) => {
  const config = TREND_CONFIG[forecast.trend];
  const Icon = config.icon;

  return (
    <div className="rounded-xl border border-border/60 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-foreground">AI 价格预测</h4>
        <span className="text-xs text-muted-text">{forecast.modelVersion}</span>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 ${config.bg}`}>
          <Icon className={`h-4 w-4 ${config.color}`} />
          <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
        </div>
        <span className={`text-lg font-bold ${forecast.trendPct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
          {forecast.trendPct >= 0 ? '+' : ''}{forecast.trendPct}%
        </span>
        <span className="text-xs text-muted-text">未来 {forecast.horizonDays} 个交易日</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-text">
              <th className="pb-2 text-left font-medium">交易日</th>
              <th className="pb-2 text-right font-medium">预测价</th>
              <th className="pb-2 text-right font-medium">区间下限</th>
              <th className="pb-2 text-right font-medium">区间上限</th>
            </tr>
          </thead>
          <tbody>
            {forecast.predictedPrices.map((price, i) => (
              <tr key={i} className="border-t border-border/30">
                <td className="py-1.5 text-secondary-text">T+{i + 1}</td>
                <td className="py-1.5 text-right font-mono text-foreground">{price.toFixed(2)}</td>
                <td className="py-1.5 text-right font-mono text-muted-text">{forecast.lowerBound[i]?.toFixed(2)}</td>
                <td className="py-1.5 text-right font-mono text-muted-text">{forecast.upperBound[i]?.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-muted-text">
        基于 {forecast.lastClose.toFixed(2)} 收盘价预测，仅供参考，不构成投资建议
      </p>
    </div>
  );
};

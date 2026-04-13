import React, { useEffect, useRef, useState } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { Play, RefreshCw, TrendingUp, Upload, Plus, Trash2, Download } from 'lucide-react';
import { useStrategyBtStore } from '../stores/strategyBtStore';
import type { StrategyBtRunRequest, StrategyBtRunDetail } from '../api/strategyBt';

/* ------------------------------------------------------------------ */
/*  Metric Card                                                        */
/* ------------------------------------------------------------------ */
const MetricCard = React.memo<{ label: string; value: string | number | null; unit?: string; color?: string; tooltip?: string }>(({
  label, value, unit = '', color, tooltip,
}) => (
  <div className="rounded-lg border border-border bg-card p-3" title={tooltip ?? undefined}>
    <p className="text-xs text-muted-foreground">{label}</p>
    <p className={`mt-1 text-lg font-semibold ${color ?? 'text-foreground'}`}>
      {value != null ? `${value}${unit}` : '—'}
      {value == null && tooltip && <span className="ml-1 text-xs font-normal text-muted-foreground">⚠</span>}
    </p>
  </div>
));

/* ------------------------------------------------------------------ */
/*  Result Dashboard                                                   */
/* ------------------------------------------------------------------ */
const ResultDashboard = React.memo<{ run: StrategyBtRunDetail }>(({ run }) => {
  const r = run.result;
  const [textReportOpen, setTextReportOpen] = useState(false);
  if (!r) return <p className="text-muted-foreground">暂无结果数据</p>;

  const returnColor = (r.totalReturnPct ?? 0) >= 0 ? 'text-green-500' : 'text-red-500';

  // Detect if trades are enriched (have entryPrice field)
  const enrichedTrades = r.tradeList.length > 0 && r.tradeList[0]?.entryPrice != null;

  return (
    <div className="space-y-6">
      {/* Text report (collapsible) */}
      {r.textReport && (
        <div className="rounded border border-border">
          <button
            className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium hover:bg-muted/50"
            onClick={() => setTextReportOpen(!textReportOpen)}
          >
            <span>📋 文字报告</span>
            <span className="text-xs text-muted-foreground">{textReportOpen ? '▲' : '▼'}</span>
          </button>
          {textReportOpen && (
            <pre className="whitespace-pre-wrap border-t border-border bg-muted/20 px-4 py-3 text-xs font-mono leading-relaxed text-foreground">
              {r.textReport}
            </pre>
          )}
        </div>
      )}

      {/* Warnings */}
      {r.benchmarkWarning && (
        <div className="rounded border border-yellow-500/50 bg-yellow-500/10 p-3 text-sm text-yellow-700 dark:text-yellow-400">
          {r.benchmarkWarning}
        </div>
      )}
      {r.warnings && r.warnings.length > 0 && r.warnings.map((w, i) => (
        <div key={i} className="rounded border border-orange-500/50 bg-orange-500/10 p-3 text-sm text-orange-700 dark:text-orange-400">
          ⚠ {w}
        </div>
      ))}
      {r.skippedCodes && r.skippedCodes.length > 0 && (
        <div className="rounded border border-yellow-500/50 bg-yellow-500/10 p-3 text-sm text-yellow-700 dark:text-yellow-400">
          以下股票因无数据被跳过: {r.skippedCodes.join(', ')}
        </div>
      )}

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <MetricCard label="总收益" value={r.totalReturnPct} unit="%" color={returnColor} />
        <MetricCard label="年化收益" value={r.annualReturnPct} unit="%" />
        <MetricCard label="Sharpe" value={r.sharpeRatio} />
        <MetricCard label="最大回撤" value={r.maxDrawdownPct} unit="%" color="text-red-500" />
        <MetricCard label="胜率" value={r.winRatePct} unit="%" />
      </div>

      {/* Secondary metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        <MetricCard label="Sortino" value={r.sortinoRatio} />
        <MetricCard label="Calmar" value={r.calmarRatio} />
        <MetricCard label="年化波动率" value={r.volatilityAnnual} unit="%" />
        <MetricCard label="VaR(95%)" value={r.var95} unit="%" />
        <MetricCard label="CVaR(95%)" value={r.cvar95} unit="%" />
        <MetricCard label="盈亏比" value={r.profitLossRatio} />
        {r.informationRatio != null && <MetricCard label="IR" value={r.informationRatio} />}
        {r.informationRatio == null && r.benchmarkWarning && <MetricCard label="IR" value={null} tooltip="基准数据不可用" />}
        {r.beta != null && <MetricCard label="Beta" value={r.beta} />}
        {r.beta == null && r.benchmarkWarning && <MetricCard label="Beta" value={null} tooltip="基准数据不可用" />}
        {r.alpha != null && <MetricCard label="Alpha" value={r.alpha} />}
        {r.alpha == null && r.benchmarkWarning && <MetricCard label="Alpha" value={null} tooltip="基准数据不可用" />}
        <MetricCard label="总交易次数" value={r.totalTrades} />
        <MetricCard label="平均持仓天数" value={r.avgHoldingDays} />
        <MetricCard label="最大连胜" value={r.maxConsecutiveWins} />
      </div>

      {/* Equity curve */}
      {r.equityCurve.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-foreground">权益曲线</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={r.equityCurve}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="value" name="策略" stroke="hsl(var(--primary))" dot={false} strokeWidth={2} />
              {r.equityCurve[0]?.benchmark != null && (
                <Line type="monotone" dataKey="benchmark" name="基准" stroke="hsl(var(--muted-foreground))" dot={false} strokeWidth={1} strokeDasharray="4 4" />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Drawdown curve */}
      {r.drawdownCurve.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-foreground">回撤曲线</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={r.drawdownCurve}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey="drawdownPct" name="回撤%" fill="hsl(var(--destructive) / 0.2)" stroke="hsl(var(--destructive))" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Monthly returns */}
      {r.monthlyReturns.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-foreground">月度收益</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={r.monthlyReturns.map((m) => ({ ...m, label: `${m.year}-${String(m.month).padStart(2, '0')}` }))}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="returnPct" name="月收益%" fill="hsl(var(--primary))" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Trade list — enriched format */}
      {r.tradeList.length > 0 && enrichedTrades && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-foreground">交易明细 ({r.tradeList.length})</h3>
          <div className="max-h-96 overflow-auto rounded border border-border">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-muted">
                <tr>
                  <th className="p-2 text-left">代码</th>
                  <th className="p-2 text-left">买入日期</th>
                  <th className="p-2 text-right">买价</th>
                  <th className="p-2 text-left">入场信号</th>
                  <th className="p-2 text-left">卖出日期</th>
                  <th className="p-2 text-right">卖价</th>
                  <th className="p-2 text-left">退出原因</th>
                  <th className="p-2 text-right">持仓高</th>
                  <th className="p-2 text-right">持仓低</th>
                  <th className="p-2 text-right">收益%</th>
                  <th className="p-2 text-right">持仓天</th>
                  <th className="p-2 text-right">盈亏</th>
                  <th className="p-2 text-right">相对基准</th>
                </tr>
              </thead>
              <tbody>
                {r.tradeList.map((t, i) => (
                  <tr key={i} className="border-t border-border hover:bg-muted/30">
                    <td className="p-2 font-mono">{t.code}</td>
                    <td className="p-2">{t.entryDate?.slice(0, 10)}</td>
                    <td className="p-2 text-right">{t.entryPrice != null ? t.entryPrice.toFixed(2) : '—'}</td>
                    <td className="p-2 text-blue-600 dark:text-blue-400">{t.entrySignal ?? '—'}</td>
                    <td className="p-2">{t.exitDate?.slice(0, 10)}</td>
                    <td className="p-2 text-right">{t.exitPrice != null ? t.exitPrice.toFixed(2) : '—'}</td>
                    <td className="p-2 text-orange-600 dark:text-orange-400">{t.exitReason ?? '—'}</td>
                    <td className="p-2 text-right text-muted-foreground">{t.highPrice != null ? t.highPrice.toFixed(2) : '—'}</td>
                    <td className="p-2 text-right text-muted-foreground">{t.lowPrice != null ? t.lowPrice.toFixed(2) : '—'}</td>
                    <td className={`p-2 text-right font-semibold ${t.returnPct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {t.returnPct >= 0 ? '+' : ''}{t.returnPct.toFixed(2)}%
                    </td>
                    <td className="p-2 text-right">{t.holdingDays}</td>
                    <td className={`p-2 text-right ${t.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {t.pnl >= 0 ? '+' : ''}{t.pnl.toLocaleString()}
                    </td>
                    <td className={`p-2 text-right ${(t.relativeReturn ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {t.relativeReturn != null ? `${t.relativeReturn >= 0 ? '+' : ''}${t.relativeReturn.toFixed(2)}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Trade list — basic format (for old data without enrichment) */}
      {r.tradeList.length > 0 && !enrichedTrades && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-foreground">交易明细 ({r.tradeList.length})</h3>
          <div className="max-h-64 overflow-auto rounded border border-border">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-muted">
                <tr>
                  <th className="p-2 text-left">代码</th>
                  <th className="p-2 text-left">买入日期</th>
                  <th className="p-2 text-left">卖出日期</th>
                  <th className="p-2 text-right">收益%</th>
                  <th className="p-2 text-right">持仓天数</th>
                  <th className="p-2 text-right">盈亏</th>
                </tr>
              </thead>
              <tbody>
                {r.tradeList.map((t, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="p-2 font-mono">{String(t.code ?? '')}</td>
                    <td className="p-2">{String(t.entryDate ?? '').slice(0, 10)}</td>
                    <td className="p-2">{String(t.exitDate ?? '').slice(0, 10)}</td>
                    <td className={`p-2 text-right font-semibold ${Number(t.returnPct ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {Number(t.returnPct ?? 0).toFixed(2)}%
                    </td>
                    <td className="p-2 text-right">{t.holdingDays ?? ''}</td>
                    <td className={`p-2 text-right ${Number(t.pnl ?? 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {Number(t.pnl ?? 0) >= 0 ? '+' : ''}{Number(t.pnl ?? 0).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Rebalance history */}
      {r.rebalanceHistory && r.rebalanceHistory.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-foreground">再平衡记录 ({r.rebalanceHistory.length} 期)</h3>
          <div className="space-y-2">
            {r.rebalanceHistory.map((entry, i) => (
              <div key={i} className="rounded border border-border p-3 text-xs">
                <div className="flex items-center gap-2 font-medium">
                  <span className="rounded bg-primary/10 px-2 py-0.5 text-primary">第 {entry.window} 期</span>
                  <span className="text-muted-foreground">{entry.start} ~ {entry.end}</span>
                </div>
                <div className="mt-1 text-muted-foreground">
                  选股 {entry.totalCodes} 只：{entry.codes.join(', ')}
                  {entry.totalCodes > entry.codes.length && ` ... (+${entry.totalCodes - entry.codes.length} 只)`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */
const StrategyBacktestPage: React.FC = () => {
  const {
    runs, currentRun, strategies, factors, customFactors, customStrategies, datasets,
    loading, initialLoading, submitting, uploading, error, warnings, runsHasMore,
    fetchRuns, fetchRun, submitBacktest,
    fetchAvailableCodes,
    uploadDataset, createCustomFactor, deleteCustomFactor,
    createCustomStrategy, deleteCustomStrategy, deleteRun, deleteDataset,
    pollRun, initializeData,
  } = useStrategyBtStore();

  const [selectedStrategies, setSelectedStrategies] = useState<string[]>(['ma_crossover']);
  const [form, setForm] = useState<StrategyBtRunRequest>({
    strategyName: 'ma_crossover',
    codes: [],
    startDate: '',
    endDate: '',
    freq: '1d',
    initialCash: 1000000,
    commission: 0.001,
    benchmark: '000300',
  });
  const [codesInput, setCodesInput] = useState('');
  const [codesError, setCodesError] = useState('');
  const pollRunRef = useRef(pollRun);
  useEffect(() => { pollRunRef.current = pollRun; }, [pollRun]);

  // Upload state
  const [uploadName, setUploadName] = useState('');
  const [uploadFreq, setUploadFreq] = useState('1d');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Custom factor state
  const [factorName, setFactorName] = useState('');
  const [factorExpr, setFactorExpr] = useState('');
  const [factorDesc, setFactorDesc] = useState('');

  // Custom strategy state
  const [stratName, setStratName] = useState('');
  const [stratBuyExpr, setStratBuyExpr] = useState('');
  const [stratSellExpr, setStratSellExpr] = useState('');
  const [stratDesc, setStratDesc] = useState('');
  const [stratRawExpr, setStratRawExpr] = useState('');
  const [buyExprError, setBuyExprError] = useState('');
  const [sellExprError, setSellExprError] = useState('');
  const [buyExprTranslated, setBuyExprTranslated] = useState('');
  const [sellExprTranslated, setSellExprTranslated] = useState('');
  const [buyValidating, setBuyValidating] = useState(false);
  const [sellValidating, setSellValidating] = useState(false);
  const [parsing, setParsing] = useState(false);
  const buyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sellTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Screening state
  const [screenUniverse, setScreenUniverse] = useState(false);
  const [screenFactors, setScreenFactors] = useState<string[]>([]);
  const [screenTopN, setScreenTopN] = useState(50);

  // Codes file upload ref
  const codesFileRef = useRef<HTMLInputElement>(null);

  // Active tab
  const [activeTab, setActiveTab] = useState<'backtest' | 'data' | 'factors' | 'strategies'>('backtest');

  useEffect(() => {
    void initializeData();
  }, [initializeData]);

  // Poll running task with exponential backoff
  const pollCountRef = useRef(0);
  const pollFailRef = useRef(0);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [pollError, setPollError] = useState('');

  useEffect(() => {
    if (!currentRun || !['pending', 'running'].includes(currentRun.status)) {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
      pollCountRef.current = 0;
      pollFailRef.current = 0;
      setPollError('');
      return;
    }
    const id = currentRun.id;
    pollCountRef.current = 0;
    pollFailRef.current = 0;
    setPollError('');
    abortRef.current = new AbortController();

    const schedulePoll = () => {
      const delay = Math.min(3000 * Math.pow(2, pollFailRef.current), 30000);
      pollTimerRef.current = setTimeout(async () => {
        if (abortRef.current?.signal.aborted) return;
        pollCountRef.current += 1;
        if (pollCountRef.current > 200) {
          setPollError('轮询超时，请手动刷新查看结果');
          return;
        }
        const ok = await pollRunRef.current(id);
        if (abortRef.current?.signal.aborted) return;
        if (ok) {
          pollFailRef.current = 0;
          setPollError('');
        } else {
          pollFailRef.current += 1;
          if (pollFailRef.current >= 5) {
            setPollError('轮询失败，请手动刷新');
            return;
          }
        }
        schedulePoll();
      }, delay);
    };
    schedulePoll();

    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
    };
  }, [currentRun?.id, currentRun?.status]);

  // Form validation state
  const [formErrors, setFormErrors] = useState<string[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    const errors: string[] = [];

    // Strategy validation
    if (selectedStrategies.length === 0) {
      errors.push('请至少选择一个策略');
    }

    // Date validation
    if (!form.startDate || !form.endDate) {
      errors.push('请填写开始和结束日期');
    } else if (form.startDate >= form.endDate) {
      errors.push('开始日期必须早于结束日期');
    }

    // Codes validation
    const codes = codesInput.split(/[,，\s\n]+/).filter(Boolean);
    if (codes.length === 0 && !screenUniverse) {
      errors.push('请输入至少一个股票代码，或开启全市场筛选');
    }
    if (codes.length > 500) {
      errors.push('股票代码不能超过 500 只');
    }
    const invalidCodes = codes.filter((c) => !/^\d{6}$/.test(c));
    if (invalidCodes.length > 0 && codes.length > 0) {
      errors.push(`无效代码（需6位数字）: ${invalidCodes.slice(0, 5).join(', ')}${invalidCodes.length > 5 ? '...' : ''}`);
    }
    const uniqueCodes = [...new Set(codes)];

    // Numeric bounds validation
    const cash = form.initialCash ?? 1000000;
    if (cash < 1000 || cash > 100000000) {
      errors.push('初始资金范围: 1,000 ~ 100,000,000');
    }
    const comm = form.commission ?? 0.001;
    if (comm < 0 || comm > 0.1) {
      errors.push('手续费率范围: 0 ~ 0.1');
    }
    if (screenUniverse && screenTopN != null && (screenTopN < 1 || screenTopN > 500)) {
      errors.push('筛选 Top N 范围: 1 ~ 500');
    }

    if (errors.length > 0) {
      setFormErrors(errors);
      setCodesError('');
      return;
    }
    setFormErrors([]);
    setCodesError('');
    let lastRunId: number | null = null;
    for (const strategyName of selectedStrategies) {
      const runId = await submitBacktest({
        ...form,
        strategyName,
        codes: uniqueCodes,
        screenUniverse,
        screenFactors: screenFactors.length > 0 ? screenFactors : undefined,
        screenTopN: screenUniverse ? screenTopN : undefined,
      });
      if (runId) lastRunId = runId;
    }
    if (lastRunId) {
      void fetchRun(lastRunId);
    }
  };

  const handleViewRun = (id: number) => {
    void fetchRun(id);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !uploadName) return;
    const ok = await uploadDataset(uploadFile, uploadName, uploadFreq);
    if (ok) {
      setUploadFile(null);
      setUploadName('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Simple frontend expression syntax pre-check
  const checkExprSyntax = (expr: string): string | null => {
    if (!expr.trim()) return '表达式不能为空';
    if (expr.length > 1000) return '表达式过长（最多 1000 字符）';
    const blocked = /(__\w+__|import|exec|eval|compile|open\s*\(|getattr|setattr|delattr|globals|locals|vars|dir\s*\(|os\.|sys\.|subprocess|shutil|lambda)/i;
    if (blocked.test(expr)) return '表达式包含不允许的关键字';
    // Check balanced parens/brackets
    let depth = 0;
    for (const ch of expr) {
      if (ch === '(' || ch === '[') depth++;
      if (ch === ')' || ch === ']') depth--;
      if (depth < 0) return '括号不匹配';
    }
    if (depth !== 0) return '括号不匹配';
    return null;
  };

  // Strategy templates
  const STRATEGY_TEMPLATES = [
    { label: 'MACD 金叉', name: 'macd_golden_cross', desc: 'MACD 金叉买入死叉卖出',
      buy: 'CROSS(EMA(C,12)-EMA(C,26), SMA(EMA(C,12)-EMA(C,26),9))',
      sell: 'CROSS(SMA(EMA(C,12)-EMA(C,26),9), EMA(C,12)-EMA(C,26))' },
    { label: 'RSI 超买超卖', name: 'rsi_oversold', desc: 'RSI14 低于30买入 高于70卖出',
      buy: 'rsi_14 < 30', sell: 'rsi_14 > 70' },
    { label: '均线多头排列', name: 'ma_bull_align', desc: 'MA5>MA10>MA20 买入，MA5<MA20 卖出',
      buy: 'MA(C,5) > MA(C,10) AND MA(C,10) > MA(C,20)', sell: 'MA(C,5) < MA(C,20)' },
    { label: '布林带突破', name: 'boll_breakout', desc: '价格突破布林带下轨买入 突破上轨卖出',
      buy: 'close < close.rolling(20).mean() - 2 * close.rolling(20).std()',
      sell: 'close > close.rolling(20).mean() + 2 * close.rolling(20).std()' },
    { label: '放量突破', name: 'vol_breakout', desc: '放量突破20日高点买入，缩量跌破20日低点卖出',
      buy: 'close > HHV(H, 20) AND volume > MA(V, 20) * 1.5',
      sell: 'close < LLV(L, 20) AND volume < MA(V, 20) * 0.5' },
  ];

  // Debounced expression validation
  const validateExprDebounced = (
    expr: string,
    setError: (e: string) => void,
    setTranslated: (t: string) => void,
    setValidating: (v: boolean) => void,
    timerRef: React.MutableRefObject<ReturnType<typeof setTimeout> | null>,
  ) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setError('');
    setTranslated('');
    if (!expr.trim()) { setValidating(false); return; }
    setValidating(true);
    timerRef.current = setTimeout(async () => {
      try {
        const { validateExpression } = await import('../api/strategyBt').then(m => m.strategyBtApi);
        const res = await validateExpression(expr);
        if (res.valid) {
          setError('');
          setTranslated(res.translated || '');
        } else {
          setError(res.error || '表达式无效');
          setTranslated('');
        }
      } catch {
        setError('验证请求失败');
      } finally {
        setValidating(false);
      }
    }, 500);
  };

  const handleBuyExprChange = (val: string) => {
    setStratBuyExpr(val);
    validateExprDebounced(val, setBuyExprError, setBuyExprTranslated, setBuyValidating, buyTimerRef);
  };

  const handleSellExprChange = (val: string) => {
    setStratSellExpr(val);
    validateExprDebounced(val, setSellExprError, setSellExprTranslated, setSellValidating, sellTimerRef);
  };

  const handleParseExpr = async () => {
    if (!stratRawExpr.trim() || parsing) return;
    setParsing(true);
    try {
      const { parseStrategyExpression } = await import('../api/strategyBt').then(m => m.strategyBtApi);
      const res = await parseStrategyExpression(stratRawExpr);
      setStratBuyExpr(res.buyExpression);
      setStratSellExpr(res.sellExpression);
      setBuyExprError('');
      setSellExprError('');
      setBuyExprTranslated('');
      setSellExprTranslated('');
      // Trigger validation on the parsed results
      validateExprDebounced(res.buyExpression, setBuyExprError, setBuyExprTranslated, setBuyValidating, buyTimerRef);
      validateExprDebounced(res.sellExpression, setSellExprError, setSellExprTranslated, setSellValidating, sellTimerRef);
    } catch {
      useStrategyBtStore.setState({ error: { title: '拆分失败', message: '表达式拆分失败', rawMessage: '', status: 400, category: 'http_error' } });
    } finally {
      setParsing(false);
    }
  };

  const applyTemplate = (t: typeof STRATEGY_TEMPLATES[0]) => {
    setStratName(t.name);
    setStratDesc(t.desc);
    setStratBuyExpr(t.buy);
    setStratSellExpr(t.sell);
    setBuyExprError('');
    setSellExprError('');
    setBuyExprTranslated('');
    setSellExprTranslated('');
    validateExprDebounced(t.buy, setBuyExprError, setBuyExprTranslated, setBuyValidating, buyTimerRef);
    validateExprDebounced(t.sell, setSellExprError, setSellExprTranslated, setSellValidating, sellTimerRef);
  };

  const handleCreateFactor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!factorName || !factorExpr) return;
    const syntaxErr = checkExprSyntax(factorExpr);
    if (syntaxErr) {
      useStrategyBtStore.setState({ error: { title: '表达式错误', message: `因子表达式错误: ${syntaxErr}`, rawMessage: syntaxErr, status: 400, category: 'http_error' } });
      return;
    }
    const ok = await createCustomFactor(factorName, factorExpr, factorDesc);
    if (ok) {
      setFactorName('');
      setFactorExpr('');
      setFactorDesc('');
    }
  };

  const handleCreateStrategy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stratName || !stratBuyExpr || !stratSellExpr) return;
    const buyErr = checkExprSyntax(stratBuyExpr);
    const sellErr = checkExprSyntax(stratSellExpr);
    if (buyErr || sellErr) {
      const msg = [buyErr && `买入: ${buyErr}`, sellErr && `卖出: ${sellErr}`].filter(Boolean).join('；');
      useStrategyBtStore.setState({ error: { title: '表达式错误', message: `策略表达式错误: ${msg}`, rawMessage: msg, status: 400, category: 'http_error' } });
      return;
    }
    const ok = await createCustomStrategy(stratName, stratBuyExpr, stratSellExpr, stratDesc);
    if (ok) {
      setStratName('');
      setStratBuyExpr('');
      setStratSellExpr('');
      setStratDesc('');
    }
  };

  const handleLoadCodes = async () => {
    await fetchAvailableCodes(form.freq ?? '1d');
    const { availableCodes: codes } = useStrategyBtStore.getState();
    if (codes.length > 0) {
      setCodesInput(codes.join(','));
      setCodesError('');
    }
  };

  const handleCodesFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const codes = text.split(/[,，\s\n\r]+/).filter(Boolean);
      setCodesInput(codes.join(','));
      setCodesError('');
    };
    reader.readAsText(file);
    if (codesFileRef.current) codesFileRef.current.value = '';
  };

  const tabClass = (tab: string) =>
    `px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
      activeTab === tab
        ? 'bg-card text-foreground border border-b-0 border-border'
        : 'text-muted-foreground hover:text-foreground'
    }`;

  const switchTab = (tab: 'backtest' | 'data' | 'factors' | 'strategies') => {
    setActiveTab(tab);
    setFormErrors([]);
    setCodesError('');
    useStrategyBtStore.setState({ error: null });
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4">
      <div className="flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold text-foreground">策略回测</h1>
      </div>

      {error && (
        <div className="rounded border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error.message}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="rounded border border-yellow-500/50 bg-yellow-500/10 p-3 text-sm text-yellow-700 dark:text-yellow-400">
          {warnings.map((w, i) => <div key={i}>{w}</div>)}
        </div>
      )}

      {pollError && (
        <div className="rounded border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {pollError}
          <button
            type="button"
            className="ml-3 underline"
            onClick={() => { if (currentRun) void fetchRun(currentRun.id); setPollError(''); }}
          >
            手动刷新
          </button>
        </div>
      )}

      {initialLoading ? (
        <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span>加载中...</span>
        </div>
      ) : (
        <div className="space-y-6">
        {/* Tabs */}
        <div className="flex gap-1 border-b border-border">
        <button type="button" className={tabClass('backtest')} onClick={() => switchTab('backtest')}>回测</button>
        <button type="button" className={tabClass('data')} onClick={() => switchTab('data')}>数据管理</button>
        <button type="button" className={tabClass('factors')} onClick={() => switchTab('factors')}>自定义因子</button>
        <button type="button" className={tabClass('strategies')} onClick={() => switchTab('strategies')}>自定义策略</button>
      </div>

      {/* ---- Data Management Tab ---- */}
      {activeTab === 'data' && (
        <div className="space-y-4">
          <form onSubmit={handleUpload} className="space-y-3 rounded-lg border border-border bg-card p-4">
            <h3 className="text-sm font-medium text-foreground">上传数据包</h3>
            <p className="text-xs text-muted-foreground">支持 .parquet / .xlsx / .csv 单文件或 .zip 压缩包（含 Excel/CSV/Parquet 文件，文件名即股票代码）</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">数据集名称</label>
                <input
                  type="text"
                  className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
                  placeholder="my_dataset"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">数据频率</label>
                <select
                  className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
                  value={uploadFreq}
                  onChange={(e) => setUploadFreq(e.target.value)}
                >
                  <option value="1d">日线</option>
                  <option value="1min">1 分钟</option>
                  <option value="5min">5 分钟</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">文件</label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".parquet,.zip,.xlsx,.xls,.csv"
                  className="w-full text-sm file:mr-2 file:rounded file:border-0 file:bg-primary/10 file:px-3 file:py-1.5 file:text-xs file:text-primary"
                  onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  required
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={uploading || !uploadFile || !uploadName}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {uploading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              {uploading ? '上传中...' : '上传'}
            </button>
          </form>

          {/* Dataset list */}
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-3 text-sm font-medium text-foreground">已注册数据集</h3>
            {datasets.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无数据集</p>
            ) : (
              <div className="space-y-2">
                {datasets.map((ds) => (
                  <div key={ds.name} className="flex items-center justify-between rounded border border-border p-2 text-sm">
                    <div>
                      <span className="font-medium">{ds.name}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{ds.source} · {ds.freq} · {ds.codeCount} 只{ds.dateRange?.[0] ? ` · ${ds.dateRange[0]} ~ ${ds.dateRange[1]}` : ''}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => { if (window.confirm(`确定删除数据集 "${ds.name}" 吗？相关数据文件也会被删除。`)) void deleteDataset(ds.name); }}
                      className="shrink-0 rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      title="删除数据集"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- Custom Factors Tab ---- */}
      {activeTab === 'factors' && (
        <div className="space-y-4">
          <form onSubmit={handleCreateFactor} className="space-y-3 rounded-lg border border-border bg-card p-4">
            <h3 className="text-sm font-medium text-foreground">创建自定义因子</h3>
            <p className="text-xs text-muted-foreground">
              可用变量: close, open, high, low, volume · 示例: (close - close.shift(5)) / close.shift(5)
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">因子名称</label>
                <input
                  type="text"
                  className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
                  placeholder="my_factor"
                  value={factorName}
                  onChange={(e) => setFactorName(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">描述（可选）</label>
                <input
                  type="text"
                  className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
                  placeholder="5 日涨幅"
                  value={factorDesc}
                  onChange={(e) => setFactorDesc(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">表达式</label>
              <input
                type="text"
                className="w-full rounded border border-border bg-background px-3 py-2 font-mono text-sm"
                placeholder="(close - close.shift(5)) / close.shift(5) 或 (C-REF(C,5))/REF(C,5)"
                value={factorExpr}
                onChange={(e) => setFactorExpr(e.target.value)}
                required
              />
              <p className="mt-1 text-xs text-muted-foreground">支持通达信公式语法（REF, MA, EMA, HHV, AND 等）和 Python 表达式</p>
            </div>
            <button
              type="submit"
              disabled={!factorName || !factorExpr}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              创建因子
            </button>
          </form>

          {/* Built-in factors */}
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-3 text-sm font-medium text-foreground">内置因子</h3>
            <div className="flex flex-wrap gap-2">
              {factors.map((f) => (
                <span key={f.name} className="rounded bg-muted px-2 py-1 text-xs">
                  {f.name} <span className="text-muted-foreground">— {f.description}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Custom factors */}
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-3 text-sm font-medium text-foreground">自定义因子</h3>
            {customFactors.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无自定义因子</p>
            ) : (
              <div className="space-y-2">
                {customFactors.map((f) => (
                  <div key={f.name} className="flex items-center justify-between rounded border border-border p-2 text-sm">
                    <div>
                      <span className="font-medium font-mono">{f.name}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{f.description}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => { if (window.confirm(`确定删除因子 "${f.name}" 吗？`)) void deleteCustomFactor(f.name); }}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- Custom Strategies Tab ---- */}
      {activeTab === 'strategies' && (
        <div className="space-y-4">
          <form onSubmit={handleCreateStrategy} className="space-y-3 rounded-lg border border-border bg-card p-4">
            <h3 className="text-sm font-medium text-foreground">创建自定义策略</h3>
            <p className="text-xs text-muted-foreground">
              通过买入/卖出条件表达式定义策略。支持通达信公式语法（REF, MA, AND 等）和 Python 表达式。可用变量：close(C), open(O), high(H), low(L), volume(V) 及所有已注册因子
            </p>

            {/* Template buttons */}
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">快速模板</label>
              <div className="flex flex-wrap gap-1.5">
                {STRATEGY_TEMPLATES.map((t) => (
                  <button
                    key={t.name}
                    type="button"
                    onClick={() => applyTemplate(t)}
                    className="rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Expression auto-split */}
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">策略表达式（粘贴完整公式，自动拆分为买入/卖出）</label>
              <div className="flex gap-2">
                <textarea
                  className="flex-1 rounded border border-border bg-background px-3 py-2 text-sm font-mono"
                  placeholder={"买入: CROSS(MA(C,5), MA(C,20))\n卖出: CROSS(MA(C,20), MA(C,5))"}
                  rows={2}
                  value={stratRawExpr}
                  onChange={(e) => setStratRawExpr(e.target.value)}
                />
                <button
                  type="button"
                  onClick={handleParseExpr}
                  disabled={!stratRawExpr.trim() || parsing}
                  className="self-end rounded-md bg-muted px-3 py-2 text-xs font-medium text-foreground hover:bg-muted/80 disabled:opacity-50"
                >
                  {parsing ? '拆分中...' : '自动拆分'}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">策略名称</label>
                <input
                  type="text"
                  className="w-full rounded border border-border bg-background px-3 py-2 text-sm font-mono"
                  placeholder="my_rsi_strategy"
                  value={stratName}
                  onChange={(e) => setStratName(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">描述（可选）</label>
                <input
                  type="text"
                  className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
                  placeholder="RSI 超卖买入超买卖出"
                  value={stratDesc}
                  onChange={(e) => setStratDesc(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">买入条件</label>
                <input
                  type="text"
                  className={`w-full rounded border bg-background px-3 py-2 text-sm font-mono ${buyExprError ? 'border-destructive' : 'border-border'}`}
                  placeholder="rsi_14 < 30"
                  value={stratBuyExpr}
                  onChange={(e) => handleBuyExprChange(e.target.value)}
                  required
                />
                {buyValidating && <p className="mt-1 text-xs text-muted-foreground">验证中...</p>}
                {buyExprError && <p className="mt-1 text-xs text-destructive">{buyExprError}</p>}
                {buyExprTranslated && <p className="mt-1 text-xs text-green-600">✓ 翻译: {buyExprTranslated}</p>}
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">卖出条件</label>
                <input
                  type="text"
                  className={`w-full rounded border bg-background px-3 py-2 text-sm font-mono ${sellExprError ? 'border-destructive' : 'border-border'}`}
                  placeholder="rsi_14 > 70"
                  value={stratSellExpr}
                  onChange={(e) => handleSellExprChange(e.target.value)}
                  required
                />
                {sellValidating && <p className="mt-1 text-xs text-muted-foreground">验证中...</p>}
                {sellExprError && <p className="mt-1 text-xs text-destructive">{sellExprError}</p>}
                {sellExprTranslated && <p className="mt-1 text-xs text-green-600">✓ 翻译: {sellExprTranslated}</p>}
              </div>
            </div>
            <button
              type="submit"
              disabled={!!buyExprError || !!sellExprError || buyValidating || sellValidating}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              <Plus className="h-4 w-4" />
              创建策略
            </button>
          </form>

          {/* Built-in strategies */}
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-3 text-sm font-medium text-foreground">可用策略</h3>
            <div className="flex flex-wrap gap-2">
              {strategies.map((s) => (
                <span key={s.name} className="rounded bg-muted px-2 py-1 text-xs">
                  {s.name} <span className="text-muted-foreground">— {s.description}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Custom strategies */}
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-3 text-sm font-medium text-foreground">自定义策略</h3>
            {customStrategies.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无自定义策略</p>
            ) : (
              <div className="space-y-2">
                {customStrategies.map((s) => (
                  <div key={s.name} className="flex items-center justify-between rounded border border-border p-2 text-sm">
                    <div>
                      <span className="font-medium font-mono">{s.name}</span>
                      {s.description && <span className="ml-2 text-xs text-muted-foreground">{s.description}</span>}
                      <div className="mt-1 text-xs text-muted-foreground">
                        <span className="text-green-600">买: {s.buyExpression}</span>
                        <span className="ml-3 text-red-500">卖: {s.sellExpression}</span>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => { if (window.confirm(`确定删除策略 "${s.name}" 吗？`)) void deleteCustomStrategy(s.name); }}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- Backtest Tab ---- */}
      {activeTab === 'backtest' && (<>
      {/* Config form */}
      <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-border bg-card p-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">策略（可多选）</label>
            <div className="max-h-40 overflow-y-auto rounded border border-border bg-background p-2 space-y-1">
              {strategies.map((s) => (
                <label key={s.name} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted/50 rounded px-1">
                  <input
                    type="checkbox"
                    checked={selectedStrategies.includes(s.name)}
                    onChange={(e) => setSelectedStrategies(prev =>
                      e.target.checked ? [...prev, s.name] : prev.filter(n => n !== s.name)
                    )}
                    className="rounded border-border"
                  />
                  {s.description || s.name}
                </label>
              ))}
              {customStrategies.map((s) => (
                <label key={s.name} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted/50 rounded px-1">
                  <input
                    type="checkbox"
                    checked={selectedStrategies.includes(s.name)}
                    onChange={(e) => setSelectedStrategies(prev =>
                      e.target.checked ? [...prev, s.name] : prev.filter(n => n !== s.name)
                    )}
                    className="rounded border-border"
                  />
                  <span className="text-primary">[自定义]</span> {s.description || s.name}
                </label>
              ))}
              {strategies.length === 0 && customStrategies.length === 0 && (
                <p className="text-xs text-muted-foreground">暂无可用策略</p>
              )}
            </div>
          </div>

          <div className="sm:col-span-2 lg:col-span-3">
            <label className="mb-1 block text-xs text-muted-foreground">
              股票代码（逗号/换行分隔）{screenUniverse && <span className="text-primary ml-1">— 已开启筛选，可留空</span>}
            </label>
            <textarea
              className={`w-full rounded border bg-background px-3 py-2 text-sm font-mono ${codesError ? 'border-destructive' : 'border-border'}`}
              placeholder="600519,300750,000001&#10;或每行一个代码"
              rows={3}
              value={codesInput}
              onChange={(e) => { setCodesInput(e.target.value); setCodesError(''); }}
            />
            {codesError && <p className="mt-1 text-xs text-destructive">{codesError}</p>}
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={handleLoadCodes}
                className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50"
              >
                <Download className="h-3 w-3" />
                从数据集加载
              </button>
              <button
                type="button"
                onClick={() => codesFileRef.current?.click()}
                className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50"
              >
                <Upload className="h-3 w-3" />
                上传代码文件
              </button>
              <input
                ref={codesFileRef}
                type="file"
                accept=".txt,.csv"
                className="hidden"
                onChange={handleCodesFileUpload}
              />
              {codesInput && (
                <span className="self-center text-xs text-muted-foreground">
                  {codesInput.split(/[,，\s\n]+/).filter(Boolean).length} 只
                </span>
              )}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">数据频率</label>
            <select
              className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
              value={form.freq}
              onChange={(e) => setForm({ ...form, freq: e.target.value })}
            >
              <option value="1d">日线</option>
              <option value="1min">1 分钟</option>
              <option value="5min">5 分钟</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">开始日期</label>
            <input
              type="date"
              className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
              value={form.startDate}
              onChange={(e) => setForm({ ...form, startDate: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">结束日期</label>
            <input
              type="date"
              className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
              value={form.endDate}
              onChange={(e) => setForm({ ...form, endDate: e.target.value })}
              required
            />
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">初始资金</label>
            <input
              type="number"
              className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
              value={form.initialCash}
              onChange={(e) => setForm({ ...form, initialCash: Number(e.target.value) })}
              min={1000}
              max={100000000}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">手续费率</label>
            <input
              type="number"
              className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
              value={form.commission}
              onChange={(e) => setForm({ ...form, commission: Number(e.target.value) })}
              min={0}
              max={0.1}
              step={0.0001}
            />
            <p className="mt-1 text-xs text-muted-foreground">默认 0.001（万分之十）</p>
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">滑点率</label>
            <input
              type="number"
              className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
              value={form.slippage ?? 0.001}
              onChange={(e) => setForm({ ...form, slippage: Number(e.target.value) })}
              min={0}
              max={0.1}
              step={0.0001}
            />
            <p className="mt-1 text-xs text-muted-foreground">默认 0.001（万分之十）</p>
          </div>
        </div>

        {/* Factors & Screening section */}
        <div className="rounded border border-border p-3 space-y-3">
          <div>
            <label className="mb-1 block text-xs text-muted-foreground">筛选因子（可多选，不选则跳过筛选）</label>
            <div className="max-h-40 overflow-y-auto rounded border border-border bg-background p-2 space-y-1">
              {factors.map((f) => (
                <label key={f.name} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted/50 rounded px-1">
                  <input
                    type="checkbox"
                    checked={screenFactors.includes(f.name)}
                    onChange={(e) => setScreenFactors(prev =>
                      e.target.checked ? [...prev, f.name] : prev.filter(n => n !== f.name)
                    )}
                    className="rounded border-border"
                  />
                  {f.name} — {f.description}
                </label>
              ))}
              {customFactors.map((f) => (
                <label key={f.name} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted/50 rounded px-1">
                  <input
                    type="checkbox"
                    checked={screenFactors.includes(f.name)}
                    onChange={(e) => setScreenFactors(prev =>
                      e.target.checked ? [...prev, f.name] : prev.filter(n => n !== f.name)
                    )}
                    className="rounded border-border"
                  />
                  <span className="text-primary">[自定义]</span> {f.name}
                </label>
              ))}
              {factors.length === 0 && customFactors.length === 0 && (
                <p className="text-xs text-muted-foreground">暂无可用因子</p>
              )}
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={screenUniverse}
              onChange={(e) => setScreenUniverse(e.target.checked)}
              className="rounded border-border"
            />
            全市场筛选（股票代码可留空，从全市场中筛选 Top N）
          </label>
          {screenUniverse && (
            <div className="sm:w-1/2">
              <label className="mb-1 block text-xs text-muted-foreground">Top N</label>
              <input
                type="number"
                className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
                value={screenTopN}
                onChange={(e) => setScreenTopN(Number(e.target.value))}
                min={1}
                max={500}
              />
              <p className="mt-1 text-xs text-muted-foreground">筛选排名前 N 的股票进行回测</p>
            </div>
          )}
        </div>

        {formErrors.length > 0 && (
          <div className="rounded border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
            {formErrors.map((err, i) => <p key={i}>{err}</p>)}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {submitting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {submitting ? '提交中...' : '运行回测'}
        </button>
      </form>

      {/* Current run result */}
      {currentRun && (
        <div className="space-y-3 rounded-lg border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-foreground">
              回测 #{currentRun.id} — {currentRun.strategyName}
            </h2>
            <span className={`rounded px-2 py-0.5 text-xs font-medium ${
              currentRun.status === 'completed' ? 'bg-green-500/10 text-green-500' :
              currentRun.status === 'failed' ? 'bg-red-500/10 text-red-500' :
              'bg-yellow-500/10 text-yellow-500'
            }`}>
              {currentRun.status}
            </span>
          </div>

          {currentRun.status === 'running' && (
            <p className="text-sm text-muted-foreground">回测运行中，自动刷新...</p>
          )}

          {currentRun.status === 'failed' && currentRun.errorMessage && (
            <p className="text-sm text-red-500">{currentRun.errorMessage}</p>
          )}

          {currentRun.status === 'completed' && <ResultDashboard run={currentRun} />}
        </div>
      )}

      {/* History list */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-foreground">历史回测</h2>
          <button
            type="button"
            onClick={() => void fetchRuns()}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>

        {runs.length === 0 && !loading && (
          <p className="text-sm text-muted-foreground">暂无回测记录</p>
        )}

        <div className="space-y-2">
          {runs.map((run) => (
            <div
              key={run.id}
              className={`flex items-center gap-2 rounded-lg border p-3 transition-colors hover:bg-muted/50 ${
                currentRun?.id === run.id ? 'border-primary' : 'border-border'
              }`}
            >
              <button
                type="button"
                onClick={() => handleViewRun(run.id)}
                className="flex-1 text-left"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">#{run.id} {run.strategyName}</span>
                  <span className={`rounded px-2 py-0.5 text-xs ${
                    run.status === 'completed' ? 'bg-green-500/10 text-green-500' :
                    run.status === 'failed' ? 'bg-red-500/10 text-red-500' :
                    'bg-yellow-500/10 text-yellow-500'
                  }`}>
                    {run.status}
                  </span>
                </div>
                <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                  <span>{run.codes?.join(', ')}</span>
                  {run.totalReturnPct != null && (
                    <span className={run.totalReturnPct >= 0 ? 'text-green-500' : 'text-red-500'}>
                      {run.totalReturnPct}%
                    </span>
                  )}
                  {run.sharpeRatio != null && <span>Sharpe: {run.sharpeRatio}</span>}
                  <span>{run.createdAt?.slice(0, 16)}</span>
                </div>
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); if (window.confirm(`确定删除回测记录 #${run.id} 吗？`)) void deleteRun(run.id); }}
                className="shrink-0 rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                title="删除回测记录"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>

        {runsHasMore && (
          <button
            type="button"
            onClick={() => void fetchRuns(runs.length)}
            disabled={loading}
            className="w-full rounded border border-border py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 disabled:opacity-50"
          >
            {loading ? '加载中...' : '加载更多'}
          </button>
        )}
      </div>
      </>)}
      </div>)}
    </div>
  );
};

export default StrategyBacktestPage;

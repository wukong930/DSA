import React, { useCallback, useEffect, useState } from 'react';
import { Filter, Hash, Plus, Star, Tag, Trash2, X } from 'lucide-react';
import { useWatchlistStore } from '../stores/watchlistStore';
import { useMonitorStore } from '../stores/monitorStore';
import { ConditionEditor } from '../components/ConditionEditor';
import type { Condition } from '../components/ConditionEditor';
import { AppPage, Card, Badge, StatusDot, EmptyState, ApiErrorAlert, ConfirmDialog, PageHeader } from '../components/common';

const MARKET_OPTIONS = [
  { value: 'cn', label: 'A股' },
  { value: 'us', label: '美股' },
  { value: 'hk', label: '港股' },
];

const MARKET_LABELS: Record<string, string> = { cn: 'A股', us: '美股', hk: '港股' };

const WatchlistPage: React.FC = () => {
  const {
    items, filterResults, loading, filtering, error,
    fetchItems, addItem, removeItem, clearFilter, filterWatchlist,
  } = useWatchlistStore();
  const { indicators, fetchIndicators } = useMonitorStore();

  const [showAddForm, setShowAddForm] = useState(false);
  const [showFilter, setShowFilter] = useState(false);
  const [stockCode, setStockCode] = useState('');
  const [stockName, setStockName] = useState('');
  const [market, setMarket] = useState('cn');
  const [tagsInput, setTagsInput] = useState('');
  const [notes, setNotes] = useState('');
  const [conditions, setConditions] = useState<Condition[]>([{ indicator: '', op: '>', value: '' }]);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  useEffect(() => {
    void fetchItems();
    void fetchIndicators();
  }, [fetchItems, fetchIndicators]);

  const handleAdd = useCallback(async () => {
    if (!stockCode.trim()) return;
    const tags = tagsInput.split(/[,，\s]+/).filter(Boolean);
    const ok = await addItem({
      stockCode: stockCode.trim(),
      stockName: stockName.trim() || undefined,
      market,
      tags: tags.length > 0 ? tags : undefined,
      notes: notes.trim() || undefined,
    });
    if (ok) {
      setShowAddForm(false);
      setStockCode('');
      setStockName('');
      setTagsInput('');
      setNotes('');
    }
  }, [stockCode, stockName, market, tagsInput, notes, addItem]);

  const handleDelete = useCallback(async () => {
    if (deleteId !== null) {
      await removeItem(deleteId);
      setDeleteId(null);
    }
  }, [deleteId, removeItem]);

  const handleFilter = useCallback(async () => {
    const valid = conditions.filter((c) => c.indicator && c.op);
    if (valid.length === 0) return;
    await filterWatchlist(
      valid.map((c) => ({
        indicator: c.indicator,
        op: c.op,
        ...(c.indicator2 ? { indicator2: c.indicator2 } : { value: Number(c.value) }),
      })),
    );
  }, [conditions, filterWatchlist]);

  // Group items by market
  const groupedByMarket = items.reduce<Record<string, typeof items>>((acc, item) => {
    const m = item.market || 'cn';
    if (!acc[m]) acc[m] = [];
    acc[m].push(item);
    return acc;
  }, {});

  // Collect all unique tags
  const allTags = [...new Set(items.flatMap((i) => i.tags || []))];

  return (
    <AppPage>
      <PageHeader title="自选股" description="管理关注的股票，按技术指标条件筛选" />

      {error ? <ApiErrorAlert error={error} className="mb-4" /> : null}

      {/* Stats bar */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--primary) / 0.12)' }}>
            <Star className="h-5 w-5 text-cyan" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{items.length}</p>
            <p className="text-xs text-muted-text">自选股</p>
          </div>
        </div>
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--status-active) / 0.12)' }}>
            <Hash className="h-5 w-5 text-success" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{Object.keys(groupedByMarket).length}</p>
            <p className="text-xs text-muted-text">覆盖市场</p>
          </div>
        </div>
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--color-purple) / 0.12)' }}>
            <Tag className="h-5 w-5 text-purple" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{allTags.length}</p>
            <p className="text-xs text-muted-text">标签分类</p>
          </div>
        </div>
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--status-triggered) / 0.12)' }}>
            <Filter className="h-5 w-5 text-warning" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{filterResults.length}</p>
            <p className="text-xs text-muted-text">筛选命中</p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="mb-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => { setShowAddForm(!showAddForm); setShowFilter(false); }}
          className="flex items-center gap-1.5 rounded-xl bg-cyan/12 px-4 py-2.5 text-sm font-medium text-cyan transition-all hover:bg-cyan/18"
        >
          <Plus className="h-4 w-4" />
          添加自选
        </button>
        <button
          type="button"
          onClick={() => { setShowFilter(!showFilter); setShowAddForm(false); }}
          className="flex items-center gap-1.5 rounded-xl border border-border/60 px-4 py-2.5 text-sm font-medium text-secondary-text transition-all hover:border-cyan/30 hover:text-foreground"
        >
          <Filter className="h-4 w-4" />
          条件筛选
        </button>
        {filterResults.length > 0 && (
          <button
            type="button"
            onClick={clearFilter}
            className="flex items-center gap-1 rounded-lg px-3 py-2 text-xs text-secondary-text transition-colors hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
            清除筛选
          </button>
        )}
      </div>

      {/* Add form */}
      {showAddForm && (
        <Card className="mb-6 border border-cyan/20" padding="lg">
          <h3 className="mb-4 text-sm font-semibold text-foreground">添加自选股</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">股票代码 *</label>
              <input
                value={stockCode}
                onChange={(e) => setStockCode(e.target.value)}
                placeholder="如 600519"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">股票名称</label>
              <input
                value={stockName}
                onChange={(e) => setStockName(e.target.value)}
                placeholder="如 贵州茅台"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">市场</label>
              <select
                value={market}
                onChange={(e) => setMarket(e.target.value)}
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              >
                {MARKET_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">标签</label>
              <input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="逗号分隔，如 白酒,核心持仓"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-2 block text-sm font-medium text-foreground">备注</label>
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="可选备注"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="rounded-xl border border-border/60 px-4 py-2 text-sm text-secondary-text transition-colors hover:text-foreground"
            >
              取消
            </button>
            <button
              type="button"
              onClick={() => void handleAdd()}
              className="rounded-xl bg-cyan/90 px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-cyan"
            >
              添加
            </button>
          </div>
        </Card>
      )}

      {/* Filter form */}
      {showFilter && (
        <Card className="mb-6 border border-purple/20" padding="lg">
          <h3 className="mb-4 text-sm font-semibold text-foreground">条件筛选</h3>
          <ConditionEditor conditions={conditions} onChange={setConditions} indicators={indicators} />
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowFilter(false)}
              className="rounded-xl border border-border/60 px-4 py-2 text-sm text-secondary-text transition-colors hover:text-foreground"
            >
              取消
            </button>
            <button
              type="button"
              onClick={() => void handleFilter()}
              disabled={filtering}
              className="rounded-xl bg-purple/90 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-purple disabled:opacity-50"
            >
              {filtering ? '筛选中...' : '开始筛选'}
            </button>
          </div>
        </Card>
      )}

      {/* Filter results */}
      {filterResults.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
            <Filter className="h-4 w-4 text-purple" />
            筛选结果
            <Badge variant="history" size="sm">{filterResults.length} 只命中</Badge>
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filterResults.map((r) => (
              <Card key={r.stockCode} className="border border-purple/15" padding="md">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-mono text-sm font-semibold text-foreground">{r.stockCode}</span>
                    {r.stockName && <span className="ml-2 text-sm text-secondary-text">{r.stockName}</span>}
                  </div>
                </div>
                <div className="mt-3 space-y-1.5">
                  {r.signals.map((s, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="text-muted-text">
                        {s.indicator} {s.op} {s.value}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-foreground">{s.actualValue.toFixed(2)}</span>
                        <StatusDot tone={s.triggered ? 'success' : 'danger'} />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Watchlist items */}
      {loading ? (
        <div className="py-16 text-center text-muted-text">加载中...</div>
      ) : items.length === 0 ? (
        <EmptyState icon={<Star className="h-10 w-10" />} title="暂无自选股" description="点击「添加自选」开始关注股票" />
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedByMarket).map(([mkt, mktItems]) => (
            <div key={mkt}>
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-secondary-text">
                <Badge variant="info" size="sm">{MARKET_LABELS[mkt] || mkt}</Badge>
                <span className="text-muted-text">{mktItems.length} 只</span>
              </h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {mktItems.map((item) => (
                  <Card key={item.id} hoverable className="group relative" padding="md">
                    {/* Delete button */}
                    <button
                      type="button"
                      onClick={() => setDeleteId(item.id)}
                      className="absolute right-3 top-3 rounded-lg p-1.5 text-muted-text opacity-0 transition-all hover:text-danger group-hover:opacity-100"
                      aria-label="删除"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>

                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--primary) / 0.08)' }}>
                        <Star className="h-5 w-5 text-cyan" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold text-foreground">{item.stockCode}</span>
                          {item.stockName && (
                            <span className="truncate text-sm text-secondary-text">{item.stockName}</span>
                          )}
                        </div>
                        {item.tags && item.tags.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {item.tags.map((tag) => (
                              <Badge key={tag} variant="default" size="sm">{tag}</Badge>
                            ))}
                          </div>
                        )}
                        {item.notes && (
                          <p className="mt-2 text-xs text-muted-text leading-relaxed">{item.notes}</p>
                        )}
                        {item.addedAt && (
                          <p className="mt-2 text-xs text-muted-text/70">
                            添加于 {new Date(item.addedAt).toLocaleDateString('zh-CN')}
                          </p>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        isOpen={deleteId !== null}
        title="移除自选股"
        message="确认从自选股中移除？"
        confirmText="移除"
        cancelText="取消"
        isDanger
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteId(null)}
      />
    </AppPage>
  );
};

export default WatchlistPage;

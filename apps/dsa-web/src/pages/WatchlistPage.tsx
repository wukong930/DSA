import React, { useCallback, useEffect, useState } from 'react';
import { Filter, Plus, Star, Trash2, X } from 'lucide-react';
import { useWatchlistStore } from '../stores/watchlistStore';
import { useMonitorStore } from '../stores/monitorStore';
import { ConditionEditor } from '../components/ConditionEditor';
import type { Condition } from '../components/ConditionEditor';
import { AppPage, Card, Badge, EmptyState, ApiErrorAlert, ConfirmDialog, PageHeader } from '../components/common';

const MARKET_OPTIONS = [
  { value: 'cn', label: 'A股' },
  { value: 'us', label: '美股' },
  { value: 'hk', label: '港股' },
];

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

  return (
    <AppPage>
      <PageHeader title="自选股" description="管理关注的股票，按技术指标条件筛选" />

      {error ? <ApiErrorAlert error={error} className="mb-4" /> : null}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => { setShowAddForm(!showAddForm); setShowFilter(false); }}
          className="btn-primary flex items-center gap-1.5 text-sm"
        >
          <Plus className="h-4 w-4" />
          添加自选股
        </button>
        <button
          type="button"
          onClick={() => { setShowFilter(!showFilter); setShowAddForm(false); }}
          className="flex items-center gap-1.5 rounded-xl border border-border/70 px-4 py-2.5 text-sm text-secondary-text transition-colors hover:border-[hsl(var(--primary))]/40 hover:text-foreground"
        >
          <Filter className="h-4 w-4" />
          条件筛选
        </button>
        {filterResults.length > 0 && (
          <button
            type="button"
            onClick={clearFilter}
            className="flex items-center gap-1 text-sm text-secondary-text hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
            清除筛选
          </button>
        )}
      </div>

      {showAddForm && (
        <Card className="mb-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="flex flex-col">
              <label className="mb-2 text-sm font-medium text-foreground">股票代码</label>
              <input
                value={stockCode}
                onChange={(e) => setStockCode(e.target.value)}
                placeholder="如 600519"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
            <div className="flex flex-col">
              <label className="mb-2 text-sm font-medium text-foreground">股票名称</label>
              <input
                value={stockName}
                onChange={(e) => setStockName(e.target.value)}
                placeholder="如 贵州茅台"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
            <div className="flex flex-col">
              <label className="mb-2 text-sm font-medium text-foreground">市场</label>
              <select
                value={market}
                onChange={(e) => setMarket(e.target.value)}
                className="input-surface input-focus-glow h-11 w-full appearance-none rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              >
                {MARKET_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value} className="bg-elevated text-foreground">{o.label}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col">
              <label className="mb-2 text-sm font-medium text-foreground">标签（逗号分隔）</label>
              <input
                value={tagsInput}
                onChange={(e) => setTagsInput(e.target.value)}
                placeholder="如 白酒,消费"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
            <div className="flex flex-col sm:col-span-2">
              <label className="mb-2 text-sm font-medium text-foreground">备注</label>
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="可选备注"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <button type="button" onClick={() => void handleAdd()} className="btn-primary text-sm">
              添加
            </button>
          </div>
        </Card>
      )}

      {showFilter && (
        <Card className="mb-6">
          <p className="mb-3 text-sm font-medium text-foreground">筛选条件</p>
          <ConditionEditor conditions={conditions} onChange={setConditions} indicators={indicators} />
          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={() => void handleFilter()}
              disabled={filtering}
              className="btn-primary text-sm"
            >
              {filtering ? '筛选中...' : '开始筛选'}
            </button>
          </div>
        </Card>
      )}

      {filterResults.length > 0 && (
        <div className="mb-6">
          <p className="mb-3 text-sm font-medium text-foreground">
            筛选结果（{filterResults.length} 只匹配）
          </p>
          <div className="space-y-3">
            {filterResults.map((r) => (
              <Card key={r.stockCode} padding="sm">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-foreground">{r.stockCode}</span>
                    {r.stockName ? <span className="ml-2 text-sm text-secondary-text">{r.stockName}</span> : null}
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {r.signals.map((s, i) => (
                    <Badge key={i} variant="info">
                      {s.indicator} {s.op} {s.value}
                    </Badge>
                  ))}
                </div>
                {Object.keys(r.indicatorSnapshot).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-secondary-text">
                    {Object.entries(r.indicatorSnapshot).map(([k, v]) => (
                      <span key={k}>{k}: {v}</span>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState icon={<Star className="h-10 w-10" />} title="暂无自选股" description="点击上方按钮添加关注的股票" />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.id} padding="sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div>
                    <span className="font-medium text-foreground">{item.stockCode}</span>
                    {item.stockName ? <span className="ml-2 text-sm text-secondary-text">{item.stockName}</span> : null}
                    <Badge className="ml-2" variant="default">
                      {item.market === 'cn' ? 'A股' : item.market === 'us' ? '美股' : '港股'}
                    </Badge>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setDeleteId(item.id)}
                  className="rounded-lg p-2 text-secondary-text transition-colors hover:text-danger"
                  aria-label="删除"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              {item.tags && item.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {item.tags.map((tag) => (
                    <Badge key={tag} variant="default">{tag}</Badge>
                  ))}
                </div>
              )}
              {item.notes ? <p className="mt-2 text-xs text-secondary-text">{item.notes}</p> : null}
              {item.addedAt ? (
                <p className="mt-1 text-xs text-muted-text">
                  添加于 {new Date(item.addedAt).toLocaleDateString('zh-CN')}
                </p>
              ) : null}
            </Card>
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

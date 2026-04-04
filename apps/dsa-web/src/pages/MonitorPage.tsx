import React, { useCallback, useEffect, useState } from 'react';
import { Activity, Bell, Plus, Trash2 } from 'lucide-react';
import { useMonitorStore } from '../stores/monitorStore';
import { ConditionEditor } from '../components/ConditionEditor';
import type { Condition } from '../components/ConditionEditor';
import { AppPage, Card, Badge, EmptyState, ApiErrorAlert, ConfirmDialog, PageHeader } from '../components/common';

const INTERVAL_OPTIONS = [
  { value: '5', label: '5 分钟' },
  { value: '15', label: '15 分钟' },
  { value: '30', label: '30 分钟' },
  { value: '60', label: '1 小时' },
];

type Tab = 'tasks' | 'alerts';

const MonitorPage: React.FC = () => {
  const {
    tasks, alerts, indicators, loading, error,
    fetchTasks, fetchAlerts, fetchIndicators,
    createTask, updateTask, deleteTask, markAlertRead,
  } = useMonitorStore();

  const [tab, setTab] = useState<Tab>('tasks');
  const [showForm, setShowForm] = useState(false);
  const [stockCode, setStockCode] = useState('');
  const [stockName, setStockName] = useState('');
  const [interval, setInterval] = useState('15');
  const [conditions, setConditions] = useState<Condition[]>([{ indicator: '', op: '>', value: '' }]);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  useEffect(() => {
    void fetchTasks();
    void fetchAlerts();
    void fetchIndicators();
  }, [fetchTasks, fetchAlerts, fetchIndicators]);

  const handleCreate = useCallback(async () => {
    if (!stockCode.trim()) return;
    const validConditions = conditions.filter((c) => c.indicator && c.op);
    if (validConditions.length === 0) return;
    const ok = await createTask({
      stockCode: stockCode.trim(),
      stockName: stockName.trim() || undefined,
      conditions: validConditions.map((c) => ({
        indicator: c.indicator,
        op: c.op,
        ...(c.indicator2 ? { indicator2: c.indicator2 } : { value: Number(c.value) }),
      })),
      intervalMinutes: Number(interval),
    });
    if (ok) {
      setShowForm(false);
      setStockCode('');
      setStockName('');
      setConditions([{ indicator: '', op: '>', value: '' }]);
    }
  }, [stockCode, stockName, conditions, interval, createTask]);

  const handleToggle = useCallback(
    (id: number, isActive: boolean) => void updateTask(id, { isActive: !isActive }),
    [updateTask],
  );

  const handleDelete = useCallback(async () => {
    if (deleteId !== null) {
      await deleteTask(deleteId);
      setDeleteId(null);
    }
  }, [deleteId, deleteTask]);

  const formatConditions = (conds: Array<Record<string, unknown>>) =>
    conds.map((c) => {
      const right = c.indicator2 || c.value;
      return `${c.indicator} ${c.op} ${right}`;
    }).join(', ');

  return (
    <AppPage>
      <PageHeader title="监控中心" description="实时监控股票技术指标，触发条件时自动告警" />

      {error ? <ApiErrorAlert error={error} className="mb-4" /> : null}

      <div className="mb-6 flex items-center gap-4 border-b border-border/40">
        {(['tasks', 'alerts'] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex items-center gap-1.5 border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
              tab === t
                ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))]'
                : 'border-transparent text-secondary-text hover:text-foreground'
            }`}
          >
            {t === 'tasks' ? <Activity className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
            {t === 'tasks' ? `任务 (${tasks.length})` : `告警 (${alerts.filter((a) => !a.isRead).length})`}
          </button>
        ))}
      </div>

      {tab === 'tasks' && (
        <>
          <div className="mb-4 flex justify-end">
            <button
              type="button"
              onClick={() => setShowForm(!showForm)}
              className="btn-primary flex items-center gap-1.5 text-sm"
            >
              <Plus className="h-4 w-4" />
              新建监控
            </button>
          </div>

          {showForm && (
            <Card className="mb-6">
              <div className="grid gap-4 sm:grid-cols-2">
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
                  <label className="mb-2 text-sm font-medium text-foreground">股票名称（可选）</label>
                  <input
                    value={stockName}
                    onChange={(e) => setStockName(e.target.value)}
                    placeholder="如 贵州茅台"
                    className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
                  />
                </div>
              </div>
              <div className="mt-4 flex flex-col">
                <label className="mb-2 text-sm font-medium text-foreground">检查间隔</label>
                <select
                  value={interval}
                  onChange={(e) => setInterval(e.target.value)}
                  className="input-surface input-focus-glow h-11 w-full appearance-none rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none sm:w-48"
                >
                  {INTERVAL_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value} className="bg-elevated text-foreground">{o.label}</option>
                  ))}
                </select>
              </div>
              <div className="mt-4">
                <label className="mb-2 block text-sm font-medium text-foreground">触发条件</label>
                <ConditionEditor conditions={conditions} onChange={setConditions} indicators={indicators} />
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <button type="button" onClick={() => setShowForm(false)} className="btn-ghost text-sm">取消</button>
                <button type="button" onClick={() => void handleCreate()} className="btn-primary text-sm">创建</button>
              </div>
            </Card>
          )}

          {loading && tasks.length === 0 ? (
            <div className="flex justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
            </div>
          ) : tasks.length === 0 ? (
            <EmptyState icon={<Activity className="h-10 w-10" />} title="暂无监控任务" description="点击「新建监控」开始监控股票指标" />
          ) : (
            <div className="space-y-3">
              {tasks.map((t) => (
                <Card key={t.id} padding="sm" className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-foreground">{t.stockCode}</span>
                      {t.stockName ? <span className="text-sm text-secondary-text">{t.stockName}</span> : null}
                      <Badge variant={t.isActive ? 'success' : 'default'}>{t.isActive ? '运行中' : '已暂停'}</Badge>
                    </div>
                    <p className="mt-1 truncate text-xs text-muted-text">
                      条件: {formatConditions(t.conditions as Array<Record<string, unknown>>)} · 间隔 {t.intervalMinutes}分钟
                    </p>
                    {t.lastCheckedAt ? (
                      <p className="text-xs text-muted-text">上次检查: {new Date(t.lastCheckedAt).toLocaleString()}</p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleToggle(t.id, t.isActive)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                        t.isActive
                          ? 'bg-warning/10 text-warning hover:bg-warning/20'
                          : 'bg-success/10 text-success hover:bg-success/20'
                      }`}
                    >
                      {t.isActive ? '暂停' : '启用'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteId(t.id)}
                      className="rounded-lg p-1.5 text-secondary-text transition-colors hover:text-danger"
                      aria-label="删除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'alerts' && (
        <>
          {alerts.length === 0 ? (
            <EmptyState icon={<Bell className="h-10 w-10" />} title="暂无告警" description="当监控条件触发时，告警会显示在这里" />
          ) : (
            <div className="space-y-3">
              {alerts.map((a) => (
                <Card key={a.id} padding="sm" className={a.isRead ? 'opacity-60' : ''}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">{a.stockCode}</span>
                        {!a.isRead ? <Badge variant="warning">未读</Badge> : null}
                      </div>
                      <p className="mt-1 text-xs text-secondary-text">
                        {JSON.stringify(a.conditionMatched)}
                      </p>
                      {a.indicatorValues && Object.keys(a.indicatorValues).length > 0 ? (
                        <div className="mt-1 flex flex-wrap gap-2">
                          {Object.entries(a.indicatorValues).map(([k, v]) => (
                            <span key={k} className="rounded bg-elevated px-1.5 py-0.5 text-xs text-muted-text">
                              {k}: {v}
                            </span>
                          ))}
                        </div>
                      ) : null}
                      {a.createdAt ? (
                        <p className="mt-1 text-xs text-muted-text">{new Date(a.createdAt).toLocaleString()}</p>
                      ) : null}
                    </div>
                    {!a.isRead ? (
                      <button
                        type="button"
                        onClick={() => void markAlertRead(a.id)}
                        className="shrink-0 rounded-lg px-2 py-1 text-xs text-secondary-text transition-colors hover:text-foreground"
                      >
                        标记已读
                      </button>
                    ) : null}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        isOpen={deleteId !== null}
        title="删除监控任务"
        message="确认删除该监控任务？删除后无法恢复。"
        confirmText="删除"
        cancelText="取消"
        isDanger
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteId(null)}
      />
    </AppPage>
  );
};

export default MonitorPage;

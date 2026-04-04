import React, { useCallback, useEffect, useState } from 'react';
import { Activity, Bell, BellRing, CheckCircle2, Clock, Plus, Radio, Trash2 } from 'lucide-react';
import { useMonitorStore } from '../stores/monitorStore';
import { ConditionEditor } from '../components/ConditionEditor';
import type { Condition } from '../components/ConditionEditor';
import { AppPage, Card, Badge, StatusDot, EmptyState, ApiErrorAlert, ConfirmDialog, PageHeader } from '../components/common';

const INTERVAL_OPTIONS = [
  { value: '5', label: '5 分钟' },
  { value: '15', label: '15 分钟' },
  { value: '30', label: '30 分钟' },
  { value: '60', label: '1 小时' },
];

const MARKET_LABELS: Record<string, string> = { cn: 'A股', us: '美股', hk: '港股' };

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

  const unreadCount = alerts.filter((a) => !a.isRead).length;
  const activeCount = tasks.filter((t) => t.isActive).length;

  const formatCondition = (c: Record<string, unknown>) => {
    const right = c.indicator2 || c.value;
    return `${c.indicator} ${c.op} ${right}`;
  };

  const formatTime = (t: string | null) => {
    if (!t) return '—';
    return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <AppPage>
      <PageHeader title="监控中心" description="实时监控股票技术指标，触发条件时自动告警" />

      {error ? <ApiErrorAlert error={error} className="mb-4" /> : null}

      {/* Stats bar */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--primary) / 0.12)' }}>
            <Radio className="h-5 w-5 text-cyan" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{tasks.length}</p>
            <p className="text-xs text-muted-text">监控任务</p>
          </div>
        </div>
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--status-active) / 0.12)' }}>
            <Activity className="h-5 w-5 text-success" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{activeCount}</p>
            <p className="text-xs text-muted-text">运行中</p>
          </div>
        </div>
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--status-triggered) / 0.12)' }}>
            <BellRing className="h-5 w-5 text-warning" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{alerts.length}</p>
            <p className="text-xs text-muted-text">总告警</p>
          </div>
        </div>
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--color-danger) / 0.12)' }}>
            <Bell className="h-5 w-5 text-danger" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{unreadCount}</p>
            <p className="text-xs text-muted-text">未读告警</p>
          </div>
        </div>
      </div>

      {/* Tabs + action */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-1 rounded-xl border border-border/60 p-1">
          <button
            type="button"
            onClick={() => setTab('tasks')}
            className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              tab === 'tasks'
                ? 'bg-cyan/12 text-cyan shadow-sm'
                : 'text-secondary-text hover:text-foreground'
            }`}
          >
            <Activity className="h-4 w-4" />
            任务
            <Badge variant="info" size="sm">{tasks.length}</Badge>
          </button>
          <button
            type="button"
            onClick={() => setTab('alerts')}
            className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              tab === 'alerts'
                ? 'bg-cyan/12 text-cyan shadow-sm'
                : 'text-secondary-text hover:text-foreground'
            }`}
          >
            <Bell className="h-4 w-4" />
            告警
            {unreadCount > 0 && <Badge variant="danger" size="sm" glow>{unreadCount}</Badge>}
          </button>
        </div>
        {tab === 'tasks' && (
          <button
            type="button"
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-1.5 rounded-xl bg-cyan px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-lg shadow-cyan/20 transition-all hover:shadow-cyan/30"
          >
            <Plus className="h-4 w-4" />
            新建监控
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && tab === 'tasks' && (
        <Card className="mb-6 border border-cyan/20" padding="lg">
          <h3 className="mb-4 text-base font-semibold text-foreground">新建监控任务</h3>
          <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">股票代码</label>
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
                placeholder="可选"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">检查间隔</label>
              <select
                value={interval}
                onChange={(e) => setInterval(e.target.value)}
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              >
                {INTERVAL_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium text-foreground">触发条件</label>
            <ConditionEditor conditions={conditions} onChange={setConditions} indicators={indicators} />
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-xl border border-border/70 px-5 py-2.5 text-sm text-secondary-text transition-colors hover:text-foreground"
            >
              取消
            </button>
            <button
              type="button"
              onClick={() => void handleCreate()}
              className="rounded-xl bg-cyan px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-lg shadow-cyan/20 transition-all hover:shadow-cyan/30"
            >
              创建
            </button>
          </div>
        </Card>
      )}

      {/* Tasks tab */}
      {tab === 'tasks' && (
        <>
          {loading ? (
            <div className="flex justify-center py-16">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/30 border-t-cyan" />
            </div>
          ) : tasks.length === 0 ? (
            <EmptyState icon={<Activity className="h-10 w-10" />} title="暂无监控任务" description="创建监控任务，实时跟踪技术指标变化" />
          ) : (
            <div className="space-y-3">
              {tasks.map((task) => (
                <Card key={task.id} className="group overflow-hidden transition-all hover:border-cyan/20" padding="none">
                  <div className="flex items-start gap-4 p-5">
                    {/* Left: status + info */}
                    <div className="flex-1 min-w-0 overflow-hidden">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <StatusDot tone={task.isActive ? 'success' : 'neutral'} pulse={task.isActive} aria-label={task.isActive ? '运行中' : '已暂停'} />
                        <span className="text-base font-semibold text-foreground">{task.stockName || task.stockCode}</span>
                        <span className="text-sm text-muted-text">{task.stockCode}</span>
                        <Badge variant={task.isActive ? 'success' : 'default'} size="sm">
                          {task.isActive ? '运行中' : '已暂停'}
                        </Badge>
                        <Badge variant="info" size="sm">{MARKET_LABELS[task.market] || task.market}</Badge>
                      </div>

                      {/* Conditions */}
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {task.conditions.map((c, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center rounded-lg border border-border/50 bg-elevated/60 px-2.5 py-1 text-xs font-mono text-secondary-text"
                          >
                            {formatCondition(c)}
                          </span>
                        ))}
                      </div>

                      {/* Meta row */}
                      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-text">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5" />
                          每 {task.intervalMinutes} 分钟
                        </span>
                        <span>上次检查: {formatTime(task.lastCheckedAt)}</span>
                        {task.lastTriggeredAt && (
                          <span className="text-warning">
                            上次触发: {formatTime(task.lastTriggeredAt)}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Right: actions */}
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleToggle(task.id, task.isActive)}
                        className={`relative h-5 w-9 rounded-full transition-colors ${
                          task.isActive ? 'bg-success' : 'bg-muted'
                        }`}
                        aria-label={task.isActive ? '暂停' : '启用'}
                      >
                        <span
                          className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${
                            task.isActive ? 'translate-x-4' : 'translate-x-0'
                          }`}
                        />
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteId(task.id)}
                        className="rounded-lg p-2 text-secondary-text transition-colors hover:text-danger"
                        aria-label="删除"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {/* Alerts tab */}
      {tab === 'alerts' && (
        <>
          {alerts.length === 0 ? (
            <EmptyState icon={<Bell className="h-10 w-10" />} title="暂无告警" description="当监控条件触发时，告警将显示在这里" />
          ) : (
            <div className="space-y-3">
              {alerts.map((a) => (
                <Card
                  key={a.id}
                  className={`transition-all ${!a.isRead ? 'border-l-2 border-l-warning' : ''}`}
                  padding="none"
                >
                  <div className="flex items-start gap-4 p-5">
                    <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                      a.isRead ? 'bg-muted' : 'bg-warning/12'
                    }`}>
                      {a.isRead
                        ? <CheckCircle2 className="h-5 w-5 text-muted-text" />
                        : <BellRing className="h-5 w-5 text-warning" />
                      }
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-foreground">{a.stockCode}</span>
                        {!a.isRead && <Badge variant="warning" size="sm">未读</Badge>}
                        {a.notifiedVia && <Badge variant="info" size="sm">{a.notifiedVia}</Badge>}
                      </div>

                      {/* Matched condition */}
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {Object.entries(a.conditionMatched)
                          .filter(([k]) => k === 'indicator' || k === 'op' || k === 'value' || k === 'actualValue')
                          .length > 0 && (
                          <span className="inline-flex items-center rounded-lg border border-warning/30 bg-warning/8 px-2.5 py-1 text-xs font-mono text-warning">
                            {a.conditionMatched.indicator as string} {a.conditionMatched.op as string} {String(a.conditionMatched.value ?? a.conditionMatched.indicator2)}
                            {a.conditionMatched.actualValue != null && (
                              <span className="ml-1.5 text-foreground">→ {String(a.conditionMatched.actualValue)}</span>
                            )}
                          </span>
                        )}
                      </div>

                      {/* Indicator snapshot */}
                      {Object.keys(a.indicatorValues).length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-text">
                          {Object.entries(a.indicatorValues).map(([k, v]) => (
                            <span key={k}>
                              <span className="text-secondary-text">{k}:</span> {typeof v === 'number' ? v.toFixed(2) : v}
                            </span>
                          ))}
                        </div>
                      )}

                      {a.createdAt && (
                        <p className="mt-2 text-xs text-muted-text">{formatTime(a.createdAt)}</p>
                      )}
                    </div>

                    {!a.isRead && (
                      <button
                        type="button"
                        onClick={() => void markAlertRead(a.id)}
                        className="shrink-0 rounded-lg border border-border/60 px-3 py-1.5 text-xs text-secondary-text transition-colors hover:border-cyan/30 hover:text-foreground"
                      >
                        标记已读
                      </button>
                    )}
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

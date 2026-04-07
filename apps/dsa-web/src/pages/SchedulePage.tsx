import React, { useCallback, useEffect, useState } from 'react';
import { Brain, Calendar, Clock, Pause, Play, Plus, Repeat, Trash2, Zap } from 'lucide-react';
import { useSchedulerStore } from '../stores/schedulerStore';
import { AppPage, Card, Badge, StatusDot, EmptyState, ApiErrorAlert, ConfirmDialog, PageHeader } from '../components/common';

const TASK_TYPE_OPTIONS = [
  { value: 'daily_analysis', label: '每日分析' },
  { value: 'custom_range', label: '自定义区间' },
];

const TASK_TYPE_LABELS: Record<string, string> = {
  daily_analysis: '每日分析',
  custom_range: '自定义区间',
  monitor: '监控',
};

const TASK_TYPE_ICONS: Record<string, React.ReactNode> = {
  daily_analysis: <Calendar className="h-4 w-4" />,
  custom_range: <Repeat className="h-4 w-4" />,
  monitor: <Zap className="h-4 w-4" />,
};

const SchedulePage: React.FC = () => {
  const { tasks, loading, error, fetchTasks, createTask, updateTask, deleteTask } = useSchedulerStore();

  const [showForm, setShowForm] = useState(false);
  const [taskName, setTaskName] = useState('');
  const [taskType, setTaskType] = useState('daily_analysis');
  const [stockCodesInput, setStockCodesInput] = useState('');
  const [scheduleType, setScheduleType] = useState('daily');
  const [hour, setHour] = useState('18');
  const [minute, setMinute] = useState('0');
  const [intervalMinutes, setIntervalMinutes] = useState('60');
  const [analysisMode, setAnalysisMode] = useState('traditional');
  const [deleteId, setDeleteId] = useState<number | null>(null);

  useEffect(() => {
    void fetchTasks();
  }, [fetchTasks]);

  const handleCreate = useCallback(async () => {
    const codes = stockCodesInput.split(/[,，\s]+/).filter(Boolean);
    if (codes.length === 0) return;

    const config: Record<string, unknown> =
      scheduleType === 'daily'
        ? { type: 'daily', hour: Number(hour), minute: Number(minute) }
        : scheduleType === 'interval'
          ? { type: 'interval', interval_minutes: Number(intervalMinutes) }
          : { type: 'cron', hour: Number(hour), minute: Number(minute) };

    const ok = await createTask({ taskType, stockCodes: codes, scheduleConfig: config, analysisMode, name: taskName || undefined });
    if (ok) {
      setShowForm(false);
      setTaskName('');
      setStockCodesInput('');
      setAnalysisMode('traditional');
    }
  }, [stockCodesInput, taskType, scheduleType, hour, minute, intervalMinutes, analysisMode, taskName, createTask]);

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

  const formatSchedule = (config: Record<string, unknown>) => {
    const type = config.type as string;
    if (type === 'daily' || type === 'cron') {
      const h = String(config.hour ?? 18).padStart(2, '0');
      const m = String(config.minute ?? 0).padStart(2, '0');
      return `${type === 'cron' ? '工作日 ' : '每天 '}${h}:${m}`;
    }
    if (type === 'interval') {
      return `每 ${config.intervalMinutes || config.interval_minutes} 分钟`;
    }
    return '未知';
  };

  const formatTime = (t: string | null) => {
    if (!t) return '—';
    return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  const activeCount = tasks.filter((t) => t.isActive).length;
  const totalStocks = new Set(tasks.flatMap((t) => t.stockCodes)).size;

  return (
    <AppPage>
      <PageHeader title="定时任务" description="管理自动化分析任务的调度计划" />

      {error ? <ApiErrorAlert error={error} className="mb-4" /> : null}

      {/* Stats bar */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--primary) / 0.12)' }}>
            <Clock className="h-5 w-5 text-cyan" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{tasks.length}</p>
            <p className="text-xs text-muted-text">调度任务</p>
          </div>
        </div>
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--status-active) / 0.12)' }}>
            <Play className="h-5 w-5 text-success" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{activeCount}</p>
            <p className="text-xs text-muted-text">运行中</p>
          </div>
        </div>
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--color-purple) / 0.12)' }}>
            <Zap className="h-5 w-5 text-purple" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{totalStocks}</p>
            <p className="text-xs text-muted-text">覆盖股票</p>
          </div>
        </div>
        <div className="terminal-card flex items-center gap-3 rounded-xl p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: 'hsl(var(--status-triggered) / 0.12)' }}>
            <Pause className="h-5 w-5 text-warning" />
          </div>
          <div>
            <p className="text-2xl font-bold text-foreground">{tasks.length - activeCount}</p>
            <p className="text-xs text-muted-text">已暂停</p>
          </div>
        </div>
      </div>

      {/* Action */}
      <div className="mb-4 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 rounded-xl bg-cyan/12 px-4 py-2.5 text-sm font-medium text-cyan transition-all hover:bg-cyan/18"
        >
          <Plus className="h-4 w-4" />
          新建任务
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <Card className="mb-6 border border-cyan/20" padding="lg">
          <h3 className="mb-4 text-base font-semibold text-foreground">新建定时任务</h3>
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">任务名称</label>
              <input
                type="text"
                value={taskName}
                onChange={(e) => setTaskName(e.target.value)}
                placeholder="可选，如 白酒组合每日追踪"
                maxLength={128}
                className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-text focus:border-cyan focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">任务类型</label>
              <div className="flex gap-2">
                {TASK_TYPE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setTaskType(opt.value)}
                    className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition-all ${
                      taskType === opt.value
                        ? 'border-cyan/40 bg-cyan/10 text-cyan'
                        : 'border-border/60 text-secondary-text hover:border-border hover:text-foreground'
                    }`}
                  >
                    {TASK_TYPE_ICONS[opt.value]}
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">股票代码</label>
              <input
                type="text"
                value={stockCodesInput}
                onChange={(e) => setStockCodesInput(e.target.value)}
                placeholder="多个代码用逗号分隔，如 600519, 000858"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
              <p className="mt-1 text-xs text-muted-text">支持 A股/港股/美股代码</p>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">调度方式</label>
              <div className="flex gap-2">
                {[
                  { value: 'daily', label: '每天', icon: <Calendar className="h-3.5 w-3.5" /> },
                  { value: 'interval', label: '固定间隔', icon: <Repeat className="h-3.5 w-3.5" /> },
                  { value: 'cron', label: '工作日', icon: <Clock className="h-3.5 w-3.5" /> },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setScheduleType(opt.value)}
                    className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition-all ${
                      scheduleType === opt.value
                        ? 'border-cyan/40 bg-cyan/10 text-cyan'
                        : 'border-border/60 text-secondary-text hover:border-border hover:text-foreground'
                    }`}
                  >
                    {opt.icon}
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {scheduleType === 'interval' ? (
              <div>
                <label className="mb-2 block text-sm font-medium text-foreground">间隔（分钟）</label>
                <input
                  type="number"
                  value={intervalMinutes}
                  onChange={(e) => setIntervalMinutes(e.target.value)}
                  className="input-surface input-focus-glow h-11 w-32 rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
                />
              </div>
            ) : (
              <div className="flex gap-3">
                <div>
                  <label className="mb-2 block text-sm font-medium text-foreground">时</label>
                  <input
                    type="number"
                    min="0"
                    max="23"
                    value={hour}
                    onChange={(e) => setHour(e.target.value)}
                    className="input-surface input-focus-glow h-11 w-20 rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-foreground">分</label>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    value={minute}
                    onChange={(e) => setMinute(e.target.value)}
                    className="input-surface input-focus-glow h-11 w-20 rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="mb-2 block text-sm font-medium text-foreground">分析模式</label>
              <div className="flex gap-2">
                {[
                  { value: 'traditional', label: '传统分析', icon: <Zap className="h-3.5 w-3.5" />, desc: '快速，单次 AI 调用' },
                  { value: 'agent', label: 'Agent 深度分析', icon: <Brain className="h-3.5 w-3.5" />, desc: '多 Agent 协作，更深入' },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setAnalysisMode(opt.value)}
                    className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition-all ${
                      analysisMode === opt.value
                        ? 'border-cyan/40 bg-cyan/10 text-cyan'
                        : 'border-border/60 text-secondary-text hover:border-border hover:text-foreground'
                    }`}
                  >
                    {opt.icon}
                    {opt.label}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-xs text-muted-text">
                {analysisMode === 'agent' ? 'Agent 模式：5个专业 Agent 多步协作分析，耗时较长但更深入' : '传统模式：单次 AI 综合分析，速度快'}
              </p>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => void handleCreate()}
                className="rounded-xl bg-cyan px-5 py-2.5 text-sm font-medium text-primary-foreground transition-all hover:opacity-90"
              >
                创建
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-xl border border-border/60 px-5 py-2.5 text-sm text-secondary-text transition-colors hover:text-foreground"
              >
                取消
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Task list */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/30 border-t-cyan" />
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState icon={<Clock className="h-10 w-10" />} title="暂无定时任务" description="创建定时任务，自动化你的分析流程" />
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <Card key={task.id} className="group transition-all hover:border-border/80" padding="none">
              <div className="flex items-start gap-4 p-5">
                {/* Left: icon */}
                <div
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
                  style={{
                    background: task.isActive
                      ? 'hsl(var(--primary) / 0.12)'
                      : 'hsl(var(--muted-text) / 0.08)',
                  }}
                >
                  {TASK_TYPE_ICONS[task.taskType] || <Clock className="h-5 w-5" />}
                </div>

                {/* Center: info */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-semibold text-foreground">
                      {task.name || TASK_TYPE_LABELS[task.taskType] || task.taskType}
                    </span>
                    <Badge variant={task.isActive ? 'success' : 'default'} size="sm">
                      <StatusDot tone={task.isActive ? 'success' : 'neutral'} className="mr-0.5" />
                      {task.isActive ? '运行中' : '已暂停'}
                    </Badge>
                    <Badge variant={task.analysisMode === 'agent' ? 'warning' : 'info'} size="sm">
                      {task.analysisMode === 'agent' ? 'Agent 模式' : '传统模式'}
                    </Badge>
                  </div>

                  {/* Stock codes */}
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {task.stockCodes.map((code) => (
                      <Badge key={code} variant="info" size="sm">{code}</Badge>
                    ))}
                  </div>

                  {/* Schedule + time info */}
                  <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-text">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatSchedule(task.scheduleConfig)}
                    </span>
                    <span>下次运行: {formatTime(task.nextRunAt)}</span>
                    <span>上次运行: {formatTime(task.lastRunAt)}</span>
                  </div>
                </div>

                {/* Right: actions */}
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    type="button"
                    onClick={() => handleToggle(task.id, task.isActive)}
                    className={`rounded-lg p-2 transition-colors ${
                      task.isActive
                        ? 'text-success hover:bg-success/10'
                        : 'text-muted-text hover:bg-muted/50'
                    }`}
                    title={task.isActive ? '暂停' : '启用'}
                    aria-label={task.isActive ? '暂停' : '启用'}
                  >
                    {task.isActive ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
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

      <ConfirmDialog
        isOpen={deleteId !== null}
        title="删除定时任务"
        message="确认删除该定时任务？删除后无法恢复。"
        confirmText="删除"
        cancelText="取消"
        isDanger
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeleteId(null)}
      />
    </AppPage>
  );
};

export default SchedulePage;

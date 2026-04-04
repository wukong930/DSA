import React, { useCallback, useEffect, useState } from 'react';
import { Clock, Plus, Trash2 } from 'lucide-react';
import { useSchedulerStore } from '../stores/schedulerStore';
import { AppPage, Card, Badge, EmptyState, ApiErrorAlert, ConfirmDialog, PageHeader } from '../components/common';

const TASK_TYPE_OPTIONS = [
  { value: 'daily_analysis', label: '每日分析' },
  { value: 'custom_range', label: '自定义区间' },
];

const TASK_TYPE_LABELS: Record<string, string> = {
  daily_analysis: '每日分析',
  custom_range: '自定义区间',
  monitor: '监控',
};

const SchedulePage: React.FC = () => {
  const { tasks, loading, error, fetchTasks, createTask, updateTask, deleteTask } = useSchedulerStore();

  const [showForm, setShowForm] = useState(false);
  const [taskType, setTaskType] = useState('daily_analysis');
  const [stockCodesInput, setStockCodesInput] = useState('');
  const [scheduleType, setScheduleType] = useState('daily');
  const [hour, setHour] = useState('18');
  const [minute, setMinute] = useState('0');
  const [intervalMinutes, setIntervalMinutes] = useState('60');
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

    const ok = await createTask({ taskType, stockCodes: codes, scheduleConfig: config });
    if (ok) {
      setShowForm(false);
      setStockCodesInput('');
    }
  }, [stockCodesInput, taskType, scheduleType, hour, minute, intervalMinutes, createTask]);

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

  return (
    <AppPage>
      <PageHeader title="定时任务" description="管理自动化分析任务的调度计划" />

      {error ? <ApiErrorAlert error={error} className="mb-4" /> : null}

      <div className="mb-4 flex justify-end">
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center gap-1.5 text-sm"
        >
          <Plus className="h-4 w-4" />
          新建任务
        </button>
      </div>

      {showForm && (
        <Card className="mb-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col">
              <label className="mb-2 text-sm font-medium text-foreground">任务类型</label>
              <select
                value={taskType}
                onChange={(e) => setTaskType(e.target.value)}
                className="input-surface input-focus-glow h-11 w-full appearance-none rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              >
                {TASK_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value} className="bg-elevated text-foreground">{o.label}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col">
              <label className="mb-2 text-sm font-medium text-foreground">股票代码（逗号分隔）</label>
              <input
                value={stockCodesInput}
                onChange={(e) => setStockCodesInput(e.target.value)}
                placeholder="如 600519, 000858"
                className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
              />
            </div>
          </div>

          <div className="mt-4">
            <label className="mb-2 block text-sm font-medium text-foreground">调度方式</label>
            <div className="flex gap-3">
              {[
                { value: 'daily', label: '每天定时' },
                { value: 'interval', label: '固定间隔' },
                { value: 'cron', label: '工作日定时' },
              ].map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => setScheduleType(o.value)}
                  className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                    scheduleType === o.value
                      ? 'border-[hsl(var(--primary))]/40 bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]'
                      : 'border-border/70 text-secondary-text hover:text-foreground'
                  }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {(scheduleType === 'daily' || scheduleType === 'cron') && (
            <div className="mt-4 flex items-center gap-2">
              <label className="text-sm text-secondary-text">执行时间</label>
              <input
                type="number"
                min={0}
                max={23}
                value={hour}
                onChange={(e) => setHour(e.target.value)}
                className="input-surface input-focus-glow h-11 w-20 rounded-xl border bg-transparent px-3 text-center text-sm transition-all focus:outline-none"
              />
              <span className="text-secondary-text">:</span>
              <input
                type="number"
                min={0}
                max={59}
                value={minute}
                onChange={(e) => setMinute(e.target.value)}
                className="input-surface input-focus-glow h-11 w-20 rounded-xl border bg-transparent px-3 text-center text-sm transition-all focus:outline-none"
              />
            </div>
          )}

          {scheduleType === 'interval' && (
            <div className="mt-4 flex items-center gap-2">
              <label className="text-sm text-secondary-text">每</label>
              <input
                type="number"
                min={1}
                value={intervalMinutes}
                onChange={(e) => setIntervalMinutes(e.target.value)}
                className="input-surface input-focus-glow h-11 w-24 rounded-xl border bg-transparent px-3 text-center text-sm transition-all focus:outline-none"
              />
              <span className="text-sm text-secondary-text">分钟执行一次</span>
            </div>
          )}

          <div className="mt-4 flex justify-end">
            <button type="button" onClick={() => void handleCreate()} className="btn-primary text-sm">
              创建任务
            </button>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState icon={<Clock className="h-10 w-10" />} title="暂无定时任务" description="点击上方按钮创建自动化分析任务" />
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <Card key={task.id} padding="sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge variant={task.isActive ? 'success' : 'default'}>
                    {task.isActive ? '运行中' : '已暂停'}
                  </Badge>
                  <Badge variant="info">{TASK_TYPE_LABELS[task.taskType] || task.taskType}</Badge>
                  <span className="text-sm text-foreground">
                    {task.stockCodes.join(', ')}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleToggle(task.id, task.isActive)}
                    className={`rounded-lg border px-3 py-1 text-xs transition-colors ${
                      task.isActive
                        ? 'border-warning/40 text-warning hover:bg-warning/10'
                        : 'border-success/40 text-success hover:bg-success/10'
                    }`}
                  >
                    {task.isActive ? '暂停' : '启用'}
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
              <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-secondary-text">
                <span>调度: {formatSchedule(task.scheduleConfig)}</span>
                {task.nextRunAt ? <span>下次运行: {new Date(task.nextRunAt).toLocaleString('zh-CN')}</span> : null}
                {task.lastRunAt ? <span>上次运行: {new Date(task.lastRunAt).toLocaleString('zh-CN')}</span> : null}
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

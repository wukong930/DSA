import React, { useState } from 'react';
import { Lightbulb, Plus, Settings2, Trash2 } from 'lucide-react';
import { Select } from './common/Select';
import { GroupedSelect } from './common/GroupedSelect';
import type { OptionGroup } from './common/GroupedSelect';
import type { IndicatorsResponse, PresetTemplate } from '../api/monitor';

export interface Condition {
  indicator: string;
  op: string;
  value: number | string;
  indicator2?: string;
}

interface ConditionEditorProps {
  conditions: Condition[];
  onChange: (conditions: Condition[]) => void;
  /** Flat indicator list (legacy fallback) */
  indicators: string[];
  /** Rich indicator data with scenarios and templates */
  indicatorData?: IndicatorsResponse | null;
}

const OPERATORS = [
  { value: '>', label: '>' },
  { value: '<', label: '<' },
  { value: '>=', label: '>=' },
  { value: '<=', label: '<=' },
  { value: '==', label: '==' },
  { value: 'cross_above', label: '上穿' },
  { value: 'cross_below', label: '下穿' },
];

const CROSS_OPS = new Set(['cross_above', 'cross_below']);

const emptyCondition = (): Condition => ({ indicator: '', op: '>', value: '' });

type EditorMode = 'template' | 'custom';

export const ConditionEditor: React.FC<ConditionEditorProps> = ({
  conditions,
  onChange,
  indicators,
  indicatorData,
}) => {
  const [mode, setMode] = useState<EditorMode>('template');

  const hasRichData = indicatorData && Object.keys(indicatorData.indicators).length > 0;
  const templates = indicatorData?.templates ?? [];
  const scenarios = indicatorData?.scenarios ?? {};

  // Build grouped options for GroupedSelect
  const indicatorGroups: OptionGroup[] = hasRichData
    ? Object.entries(indicatorData!.indicators).map(([scenarioKey, items]) => ({
        label: scenarios[scenarioKey] || scenarioKey,
        options: items.map((item) => ({
          value: item.name,
          label: `${item.cnName}`,
          description: item.cnDesc,
        })),
      }))
    : [];

  // Flat options fallback
  const flatOptions = indicators.map((i) => ({ value: i, label: i }));

  // Lookup map: indicator name → cnName
  const cnNameMap = new Map<string, string>();
  if (hasRichData) {
    for (const items of Object.values(indicatorData!.indicators)) {
      for (const item of items) {
        cnNameMap.set(item.name, item.cnName);
      }
    }
  }

  const update = (index: number, patch: Partial<Condition>) => {
    const next = conditions.map((c, i) => (i === index ? { ...c, ...patch } : c));
    onChange(next);
  };

  const add = () => onChange([...conditions, emptyCondition()]);
  const remove = (index: number) => onChange(conditions.filter((_, i) => i !== index));

  const applyTemplate = (template: PresetTemplate) => {
    const newConditions: Condition[] = template.conditions.map((c) => ({
      indicator: c.indicator,
      op: c.op,
      value: c.value ?? '',
      indicator2: c.indicator2,
    }));
    onChange(newConditions);
  };

  return (
    <div className="space-y-4">
      {/* Mode toggle */}
      {hasRichData && templates.length > 0 ? (
        <div className="flex gap-1 rounded-xl border border-border/60 p-1 w-fit">
          <button
            type="button"
            onClick={() => setMode('template')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
              mode === 'template'
                ? 'bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))] shadow-sm'
                : 'text-secondary-text hover:text-foreground'
            }`}
          >
            <Lightbulb className="h-3.5 w-3.5" />
            快捷模板
          </button>
          <button
            type="button"
            onClick={() => setMode('custom')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
              mode === 'custom'
                ? 'bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))] shadow-sm'
                : 'text-secondary-text hover:text-foreground'
            }`}
          >
            <Settings2 className="h-3.5 w-3.5" />
            自定义条件
          </button>
        </div>
      ) : null}

      {/* Template mode */}
      {mode === 'template' && hasRichData && templates.length > 0 ? (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {templates.map((tpl) => (
            <button
              key={tpl.key}
              type="button"
              onClick={() => applyTemplate(tpl)}
              className="group flex flex-col items-start gap-1 rounded-xl border border-border/60 p-3 text-left transition-all hover:border-[hsl(var(--primary)/0.4)] hover:bg-[hsl(var(--primary)/0.05)]"
            >
              <span className="text-sm font-medium text-foreground">{tpl.name}</span>
              <span className="text-xs text-muted-text line-clamp-2">{tpl.description}</span>
            </button>
          ))}
        </div>
      ) : null}

      {/* Custom mode or fallback */}
      {(mode === 'custom' || !hasRichData || templates.length === 0) ? (
        <div className="space-y-3">
          {conditions.map((cond, idx) => {
            const isCross = CROSS_OPS.has(cond.op);
            return (
              <div key={idx} className="flex items-end gap-2">
                <div className="flex-1 min-w-0">
                  {hasRichData ? (
                    <GroupedSelect
                      value={cond.indicator}
                      onChange={(v) => update(idx, { indicator: v })}
                      groups={indicatorGroups}
                      placeholder="选择指标"
                      label={idx === 0 ? '指标' : undefined}
                    />
                  ) : (
                    <Select
                      value={cond.indicator}
                      onChange={(v) => update(idx, { indicator: v })}
                      options={flatOptions}
                      placeholder="指标"
                      label={idx === 0 ? '指标' : undefined}
                    />
                  )}
                </div>
                <div className="w-28 shrink-0">
                  <Select
                    value={cond.op}
                    onChange={(v) => {
                      const patch: Partial<Condition> = { op: v };
                      if (CROSS_OPS.has(v) && !cond.indicator2) {
                        patch.indicator2 = '';
                        patch.value = '';
                      }
                      if (!CROSS_OPS.has(v)) {
                        patch.indicator2 = undefined;
                      }
                      update(idx, patch);
                    }}
                    options={OPERATORS}
                    placeholder="运算符"
                    label={idx === 0 ? '运算符' : undefined}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  {isCross ? (
                    hasRichData ? (
                      <GroupedSelect
                        value={cond.indicator2 || ''}
                        onChange={(v) => update(idx, { indicator2: v, value: '' })}
                        groups={indicatorGroups}
                        placeholder="对比指标"
                        label={idx === 0 ? '对比指标' : undefined}
                      />
                    ) : (
                      <Select
                        value={cond.indicator2 || ''}
                        onChange={(v) => update(idx, { indicator2: v, value: '' })}
                        options={flatOptions}
                        placeholder="对比指标"
                        label={idx === 0 ? '对比指标' : undefined}
                      />
                    )
                  ) : (
                    <div className="flex flex-col">
                      {idx === 0 ? <label className="mb-2 text-sm font-medium text-foreground">阈值</label> : null}
                      <input
                        type="number"
                        value={cond.value}
                        onChange={(e) => update(idx, { value: e.target.value === '' ? '' : Number(e.target.value) })}
                        placeholder="数值"
                        className="input-surface input-focus-glow h-11 w-full rounded-xl border bg-transparent px-4 text-sm transition-all focus:outline-none"
                      />
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => remove(idx)}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-border/70 text-secondary-text transition-colors hover:border-danger/40 hover:text-danger"
                  aria-label="删除条件"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            );
          })}
          <button
            type="button"
            onClick={add}
            className="flex items-center gap-1.5 text-sm text-secondary-text transition-colors hover:text-foreground"
          >
            <Plus className="h-4 w-4" />
            添加条件
          </button>
        </div>
      ) : null}

      {/* Show current conditions summary when in template mode and conditions exist */}
      {mode === 'template' && conditions.length > 0 && conditions[0].indicator ? (
        <div className="rounded-xl border border-border/40 bg-elevated/40 p-3">
          <p className="mb-2 text-xs font-medium text-secondary-text">当前条件</p>
          <div className="flex flex-wrap gap-1.5">
            {conditions.map((c, i) => (
              <span
                key={i}
                className="inline-flex items-center rounded-lg border border-border/50 bg-elevated/60 px-2.5 py-1 text-xs font-mono text-secondary-text"
              >
                {cnNameMap.get(c.indicator) || c.indicator} {c.op} {c.indicator2 ? (cnNameMap.get(c.indicator2) || c.indicator2) : c.value}
              </span>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setMode('custom')}
            className="mt-2 text-xs text-[hsl(var(--primary))] hover:underline"
          >
            编辑条件
          </button>
        </div>
      ) : null}
    </div>
  );
};

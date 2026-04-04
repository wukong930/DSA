import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Select } from './common/Select';

export interface Condition {
  indicator: string;
  op: string;
  value: number | string;
  indicator2?: string;
}

interface ConditionEditorProps {
  conditions: Condition[];
  onChange: (conditions: Condition[]) => void;
  indicators: string[];
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

export const ConditionEditor: React.FC<ConditionEditorProps> = ({ conditions, onChange, indicators }) => {
  const indicatorOptions = indicators.map((i) => ({ value: i, label: i }));

  const update = (index: number, patch: Partial<Condition>) => {
    const next = conditions.map((c, i) => (i === index ? { ...c, ...patch } : c));
    onChange(next);
  };

  const add = () => onChange([...conditions, emptyCondition()]);

  const remove = (index: number) => onChange(conditions.filter((_, i) => i !== index));

  return (
    <div className="space-y-3">
      {conditions.map((cond, idx) => {
        const isCross = CROSS_OPS.has(cond.op);
        return (
          <div key={idx} className="flex items-end gap-2">
            <div className="flex-1 min-w-0">
              <Select
                value={cond.indicator}
                onChange={(v) => update(idx, { indicator: v })}
                options={indicatorOptions}
                placeholder="指标"
                label={idx === 0 ? '指标' : undefined}
              />
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
                <Select
                  value={cond.indicator2 || ''}
                  onChange={(v) => update(idx, { indicator2: v, value: '' })}
                  options={indicatorOptions}
                  placeholder="对比指标"
                  label={idx === 0 ? '对比指标' : undefined}
                />
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
  );
};

# DSA Web UI 重设计方案

---

## 一、现状分析

### 1.1 优势

- **技术栈成熟**：React 19 + Tailwind CSS 4 + Zustand + Recharts，现代前端最佳实践
- **设计令牌体系**：`:root` 中定义了 HSL 格式的语义化 CSS 变量，支持 light/dark 双主题
- **组件化程度高**：Card、Button、Badge、Input、Select、EmptyState、Tooltip、Pagination 等基础组件齐全
- **布局结构清晰**：Shell + SidebarNav + AppPage 三层嵌套，侧边栏有 motion layoutId 平滑动画
- **首页和聊天页完成度高**：glassmorphism 面板、gradient border、sentiment gauge 等高级视觉效果

### 1.2 问题

| 问题 | 现状 | 影响 |
|------|------|------|
| CSS 变量爆炸 | index.css 2891 行，`--home-*` 约 50 个、`--settings-*` 约 30 个、`--login-*` 约 35 个 | 维护困难，同一语义重复定义 |
| 圆角不一致 | Card 用 `rounded-2xl`，glass-panel 用 `rounded-3xl`，Dialog 用 `rounded-xl` | 视觉不统一 |
| 阴影过多 | 10+ 种阴影定义 + 8 种 glow boxShadow | 难以选择，增加认知负担 |
| Button 变体过多 | 12 个 variant，其中 `action-primary` 与 `home-action-ai` 完全相同 | 冗余，增加维护成本 |
| 页面完成度差异大 | HomePage/ChatPage 丰富，MonitorPage/WatchlistPage/SchedulePage 仅基础 CRUD | 体验割裂 |
| opacity 滥用 | `bg-card/70`、`bg-card/85`、`border-border/60` 等无统一阶梯 | 视觉不一致 |
| 缺少统一间距系统 | AppPage 用 `px-4 md:px-6`，Shell 用 `px-3 sm:px-4`，随意混用 | 排版松散 |
| 缺少金融色彩语义 | 未定义 A 股"红涨绿跌"专用变量 | 不符合中国市场惯例 |

---

## 二、设计理念

### 2.1 定位：专业金融工作台 (Professional Financial Workstation)

**参考对象**：
- Bloomberg Terminal — 信息密度与专业感
- TradingView — 现代化图表交互与深色主题
- 同花顺 iFinD — 中国市场数据展示惯例
- 东方财富 Choice — 多面板布局
- Robinhood — 简洁交互与渐变色运用

**核心原则**：

1. **信息密度优先** — 金融用户需要单屏获取尽可能多的关键数据，减少装饰性留白
2. **数据即界面** — 数字、图表、状态指示器是核心 UI 元素，用可视化替代纯文字
3. **一致性即信任** — 统一圆角、阴影、间距、颜色语义，相同功能保持相同视觉
4. **暗色主题为主** — 长时间盯盘减少视觉疲劳，暗色背景数据色彩对比度更高

---

## 三、配色方案

### 3.1 基础色板

#### 深色主题（主题）

```css
:root.dark {
  /* 背景层级 */
  --bg-base:      hsl(220 18% 7%);     /* #0f1118 最底层 */
  --bg-surface:   hsl(220 16% 10%);    /* #161921 卡片/面板 */
  --bg-elevated:  hsl(220 14% 13%);    /* #1d2029 弹窗/浮层 */
  --bg-hover:     hsl(220 14% 16%);    /* #242730 悬停态 */

  /* 文字层级 */
  --text-primary:   hsl(220 20% 93%);  /* #e8eaf0 主文字 */
  --text-secondary: hsl(220 14% 62%);  /* #949bab 次要文字 */
  --text-muted:     hsl(220 10% 42%);  /* #636a78 辅助文字 */

  /* 边框 */
  --border-default: hsl(220 14% 18%);  /* #282c38 默认边框 */
  --border-hover:   hsl(220 14% 24%);  /* #363a48 悬停边框 */
}
```

#### 浅色主题

```css
:root {
  --bg-base:      hsl(220 20% 97%);    /* #f5f6f8 */
  --bg-surface:   hsl(0 0% 100%);      /* #ffffff */
  --bg-elevated:  hsl(0 0% 100%);      /* #ffffff */
  --bg-hover:     hsl(220 20% 94%);    /* #eceef2 */

  --text-primary:   hsl(220 25% 12%);  /* #171c28 */
  --text-secondary: hsl(220 12% 38%);  /* #555e6e */
  --text-muted:     hsl(220 8% 55%);   /* #858a94 */

  --border-default: hsl(220 18% 88%);  /* #d8dce4 */
  --border-hover:   hsl(220 18% 80%);  /* #c4c9d4 */
}
```

### 3.2 品牌色与功能色

```css
:root {
  /* 品牌主色 — 保持 Cyan，微调饱和度 */
  --color-primary:     hsl(193 90% 45%);   /* 主色 */
  --color-primary-dim: hsl(193 80% 35%);   /* 暗态 */
  --color-primary-glow: hsl(193 90% 45% / 0.15); /* 光晕 */

  /* 辅助色 — 保持 Purple */
  --color-accent:      hsl(247 80% 64%);
  --color-accent-dim:  hsl(247 70% 54%);

  /* A 股涨跌色（红涨绿跌） */
  --stock-up:    hsl(0 85% 55%);       /* 红色 — 上涨 */
  --stock-down:  hsl(152 65% 40%);     /* 绿色 — 下跌 */
  --stock-flat:  hsl(220 10% 50%);     /* 灰色 — 平盘 */

  /* 语义色 */
  --color-success: hsl(152 65% 40%);   /* 成功 */
  --color-warning: hsl(37 90% 50%);    /* 警告 */
  --color-danger:  hsl(0 85% 55%);     /* 危险 */
  --color-info:    hsl(210 80% 55%);   /* 信息 */
}
```

### 3.3 透明度阶梯（统一规范）

```css
:root {
  /* 只使用 5 档透明度，杜绝随意值 */
  --alpha-subtle:  0.05;  /* 背景微着色 */
  --alpha-light:   0.10;  /* 轻量背景 */
  --alpha-medium:  0.20;  /* 中等强调 */
  --alpha-strong:  0.40;  /* 强调 */
  --alpha-solid:   0.80;  /* 接近实色 */
}
```

---

## 四、布局优化

### 4.1 全局布局结构

```
┌──────────────────────────────────────────────────┐
│ TopBar (h-12, sticky)                            │
│ Logo · 搜索框 · 主题切换 · 通知 · 用户           │
├────────┬─────────────────────────────────────────┤
│        │                                         │
│ Sidebar│  Content Area                           │
│ (w-56) │  (max-w-[1440px], mx-auto)             │
│        │  ┌─────────────────────────────────┐    │
│ 首页   │  │ PageHeader                      │    │
│ 问股   │  ├─────────────────────────────────┤    │
│ 持仓   │  │                                 │    │
│ 监控   │  │ Page Content                    │    │
│ 自选股 │  │                                 │    │
│ 定时   │  │                                 │    │
│ 回测   │  │                                 │    │
│ 设置   │  └─────────────────────────────────┘    │
│        │                                         │
└────────┴─────────────────────────────────────────┘
```

### 4.2 侧边栏改进

| 属性 | 当前 | 建议 |
|------|------|------|
| 宽度 | 116px (展开) / 64px (收起) | 224px (展开) / 64px (收起) |
| 内容 | 仅图标 + 短标签 | 图标 + 完整标签 + 描述文字 |
| 分组 | 无 | 分为"分析"和"管理"两组 |
| 底部 | 无 | 折叠按钮 + 版本号 |

```
分析
  ├─ 首页        概览与分析
  ├─ 问股        AI 智能问答
  ├─ 持仓        账户与交易
  └─ 回测        策略验证
管理
  ├─ 监控        实时告警
  ├─ 自选股      关注列表
  ├─ 定时任务    自动调度
  └─ 设置        系统配置
```

### 4.3 响应式断点

```
sm:  640px   — 单列布局，侧边栏隐藏为 drawer
md:  768px   — 侧边栏收起态（64px）
lg:  1024px  — 侧边栏展开态（224px）
xl:  1280px  — 内容区双栏布局
2xl: 1536px  — 内容区三栏布局（仪表盘）
```

### 4.4 间距系统（统一规范）

```
页面外边距:  px-4 sm:px-6 lg:px-8  （统一所有页面）
卡片内边距:  p-4 (紧凑) | p-5 (默认) | p-6 (宽松)
组件间距:    gap-3 (紧凑) | gap-4 (默认) | gap-6 (分区)
区块间距:    space-y-4 (同类) | space-y-6 (不同类) | space-y-8 (大区块)
```

---

## 五、组件规范

### 5.1 圆角统一

```
--radius-sm:  6px    — Badge、Tag、小按钮
--radius-md:  8px    — Input、Select、小卡片
--radius-lg:  12px   — Card、Dialog、大按钮
--radius-xl:  16px   — 面板、浮层
--radius-full: 9999px — Avatar、Pill
```

**规则**：Card 统一 `rounded-lg`(12px)，Dialog 统一 `rounded-xl`(16px)，Button 统一 `rounded-lg`(12px)。

### 5.2 阴影精简（3 档）

```css
--shadow-sm:   0 1px 3px hsl(220 20% 10% / 0.08);                          /* 卡片默认 */
--shadow-md:   0 4px 12px hsl(220 20% 10% / 0.12);                         /* 悬停/浮层 */
--shadow-lg:   0 12px 32px hsl(220 20% 10% / 0.16), 0 4px 8px hsl(220 20% 10% / 0.08); /* 弹窗/Drawer */
--shadow-glow: 0 0 16px hsl(193 90% 45% / 0.15);                           /* 品牌光晕（仅特殊场景） */
```

### 5.3 Button 精简为 5 个变体

| 变体 | 用途 | 样式 |
|------|------|------|
| `primary` | 主要操作（提交、确认） | 实色 Cyan 背景 |
| `secondary` | 次要操作（取消、返回） | 透明背景 + 边框 |
| `ghost` | 轻量操作（筛选、切换） | 无边框，hover 显示背景 |
| `danger` | 危险操作（删除、重置） | 红色背景或红色文字 |
| `icon` | 图标按钮（关闭、更多） | 圆形/方形，无文字 |

删除 `gradient`、`danger-subtle`、`settings-primary`、`settings-secondary`、`action-primary`、`action-secondary`、`home-action-ai`、`home-action-report`。

### 5.4 表单组件统一

```
Input / Select / Textarea:
  高度: h-10 (默认) | h-9 (紧凑)
  圆角: rounded-md (8px)
  边框: border-default, focus:border-primary
  背景: bg-surface (深色) | bg-white (浅色)
  内边距: px-3
  字号: text-sm (14px)
```

### 5.5 DataTable 组件（新增）

当前 Monitor/Watchlist/Schedule 页面使用 Card 列表展示数据，信息密度低。建议新增 DataTable 组件：

```
特性:
  - 固定表头 (sticky header)
  - 列排序 (sortable columns)
  - 行悬停高亮
  - 紧凑/默认两种密度
  - 响应式：小屏自动切换为 Card 列表
```

### 5.6 StatusDot 组件（新增）

用于监控任务、定时任务的运行状态指示：

```
● 绿色 (active/running)  — 正常运行
● 黄色 (warning/paused)  — 暂停/警告
● 红色 (error/stopped)   — 错误/停止
● 灰色 (inactive/idle)   — 未激活
```

---

## 六、页面级设计建议

### 6.1 首页 (/) — 微调

当前完成度高，仅需微调：
- 统一使用新的阴影和圆角令牌
- 删除 `--home-*` 专属变量，改用全局令牌
- 股票涨跌色改用 `--stock-up` / `--stock-down`

### 6.2 问股 (/chat) — 微调

- 统一消息气泡圆角
- 删除 `--chat-*` 专属变量

### 6.3 持仓 (/portfolio) — 中度优化

- 顶部增加 Portfolio Summary Bar：总资产、日盈亏（带涨跌色）、总收益率
- 持仓列表改为 DataTable，增加列：当前价、成本价、盈亏额、盈亏率
- 交易记录增加买卖方向色彩标识（买入用 `--stock-up`，卖出用 `--stock-down`）

### 6.4 监控 (/monitor) — 重点改造

当前仅基础 CRUD 列表，缺乏实时监控的视觉感受。

```
┌─────────────────────────────────────────────────┐
│ PageHeader: 监控中心                    [+ 新建] │
├─────────────────────────────────────────────────┤
│ 监控概览 (StatCard x3)                           │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│ │ 活跃任务  │ │ 今日告警  │ │  触发率   │         │
│ │    12    │ │    5     │ │   42%    │         │
│ └──────────┘ └──────────┘ └──────────┘         │
├────────────────────────┬────────────────────────┤
│ 监控任务列表 (DataTable) │ 告警时间线 (Timeline)   │
│ 股票 | 条件 | 间隔 |状态 │ ● 14:32 600519 触发    │
│ ──────────────────── │ ● 14:15 000858 触发    │
│ 600519 | MA5>MA20    │ ● 13:48 601318 触发    │
│         | 15min | 🟢  │                        │
│ 000858 | RSI<30      │                        │
│         | 30min | 🟢  │                        │
└────────────────────────┴────────────────────────┘
```

改动要点：
- 顶部 3 个 StatCard：活跃任务数、今日告警数、告警触发率
- 任务列表从 Card 改为 DataTable，增加 StatusDot、最后检查时间
- 右侧增加告警时间线，按时间倒序，带股票名称和触发条件
- 新建表单改为 SlideOver（右侧抽屉），不再跳转空白页

### 6.5 自选股 (/watchlist) — 重点改造

```
┌─────────────────────────────────────────────────┐
│ PageHeader: 自选股                [筛选] [+ 添加] │
├─────────────────────────────────────────────────┤
│ DataTable                                        │
│ 代码   | 名称   | 市场 | 现价  | 涨跌幅 | 标签   │
│ ─────────────────────────────────────────────── │
│ 600519 | 贵州茅台| A股  | 1680 | +2.3%  | 白酒   │
│ 000858 | 五粮液  | A股  | 148  | -1.2%  | 白酒   │
│ AAPL   | 苹果    | 美股 | 195  | +0.8%  | 科技   │
│ ─────────────────────────────────────────────── │
│ 条件筛选面板 (Collapsible)                        │
│ ┌─────────────────────────────────────────────┐ │
│ │ [指标 ▼] [运算符 ▼] [值    ] [+ 添加条件]    │ │
│ │ [执行筛选]                                   │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

改动要点：
- 从 Card 列表改为 DataTable，增加实时行情列（现价、涨跌幅带涨跌色）
- 条件筛选改为可折叠面板（Collapsible），不再跳转
- 支持按标签分组查看
- 支持列排序（按涨跌幅、按市场）

### 6.6 定时任务 (/schedule) — 重点改造

```
┌─────────────────────────────────────────────────┐
│ PageHeader: 定时任务                    [+ 新建] │
├─────────────────────────────────────────────────┤
│ 概览 (StatCard x3)                               │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│ │ 活跃任务  │ │ 今日执行  │ │ 成功率    │         │
│ │    8     │ │    3     │ │   100%   │         │
│ └──────────┘ └──────────┘ └──────────┘         │
├─────────────────────────────────────────────────┤
│ DataTable                                        │
│ 名称 | 类型 | 时间/间隔 | 下次执行 | 状态 | 操作  │
│ ──────────────────────────────────────────────  │
│ 每日分析 | 每日 | 09:30 | 明天 09:30 | 🟢 | ⋯   │
│ 盘后复盘 | 每日 | 15:30 | 明天 15:30 | 🟢 | ⋯   │
│ 周报汇总 | 每周 | 周五   | 04/11     | 🟡 | ⋯   │
└─────────────────────────────────────────────────┘
```

改动要点：
- 顶部 StatCard 概览
- 任务列表改为 DataTable，增加"下次执行"倒计时、StatusDot
- 新建表单改为 SlideOver

### 6.7 回测 (/backtest) — 中度优化

- 回测结果增加 Equity Curve 折线图
- 关键指标用 StatCard 展示（胜率、年化收益、最大回撤、夏普比率）
- 删除 `--backtest-*` 专属变量

### 6.8 设置 (/settings) — 微调

- 删除 `--settings-*` 专属变量，统一使用全局令牌
- 表单组件统一为新规范

---

## 七、交互优化

### 7.1 加载状态

```
页面级:  Skeleton Screen（骨架屏），模拟最终布局形状
组件级:  Spinner（小型旋转指示器）
按钮级:  disabled + Spinner 替换文字
表格级:  行级 Shimmer 动画
```

### 7.2 空状态

每个列表页面定义专属空状态插画和引导文案：

| 页面 | 空状态文案 | 引导操作 |
|------|-----------|---------|
| 监控 | "还没有监控任务" | "创建第一个监控" 按钮 |
| 自选股 | "自选股列表为空" | "添加股票" 按钮 |
| 定时任务 | "暂无定时任务" | "创建定时任务" 按钮 |
| 回测 | "还没有回测记录" | "开始回测" 按钮 |

### 7.3 动画规范

```css
/* 统一过渡时长 */
--duration-fast:   100ms;  /* hover、focus */
--duration-normal: 200ms;  /* 展开、折叠 */
--duration-slow:   300ms;  /* 页面切换、Drawer */

/* 统一缓动函数 */
--ease-default: cubic-bezier(0.4, 0, 0.2, 1);
--ease-spring:  cubic-bezier(0.34, 1.56, 0.64, 1);
```

### 7.4 表单交互

- 新建/编辑表单统一使用 SlideOver（右侧抽屉），不再内联展开
- 表单验证使用 inline error（字段下方红色提示），不使用 toast
- 提交成功使用 toast 通知

---

## 八、数据可视化

### 8.1 图表配色

```css
/* 图表系列色（6 色循环） */
--chart-1: hsl(193 90% 45%);   /* Cyan — 主系列 */
--chart-2: hsl(247 80% 64%);   /* Purple — 次系列 */
--chart-3: hsl(37 90% 50%);    /* Amber */
--chart-4: hsl(152 65% 40%);   /* Emerald */
--chart-5: hsl(340 75% 55%);   /* Rose */
--chart-6: hsl(210 80% 55%);   /* Blue */
```

### 8.2 金融数据展示规范

| 数据类型 | 格式 | 颜色 |
|---------|------|------|
| 股价上涨 | +2.35% | `--stock-up` (红) |
| 股价下跌 | -1.28% | `--stock-down` (绿) |
| 股价平盘 | 0.00% | `--stock-flat` (灰) |
| 金额 | ¥1,680.00 | `--text-primary` |
| 成交量 | 12.5万手 | `--text-secondary` |
| 时间戳 | 14:32:05 | `--text-muted` |

### 8.3 迷你图 (Sparkline)

在 DataTable 中嵌入迷你走势图：
- 尺寸：80px × 24px
- 无坐标轴、无标签
- 上涨趋势用 `--stock-up`，下跌用 `--stock-down`
- 用于自选股列表的"近期走势"列

---

## 九、实施路线图

### Phase 1: 基础令牌统一（1-2 天）

1. 精简 CSS 变量：删除所有 `--home-*`、`--settings-*`、`--login-*`、`--chat-*`、`--backtest-*` 页面专属变量，统一为全局令牌
2. 统一圆角：Card → `rounded-lg`，Dialog → `rounded-xl`，Button → `rounded-lg`
3. 精简阴影为 3 档
4. 统一透明度为 5 档
5. 添加金融语义色变量（`--stock-up/down/flat`）
6. Button 变体从 12 个精简为 5 个

### Phase 2: 核心组件升级（2-3 天）

1. 新增 DataTable 组件
2. 新增 StatusDot 组件
3. 新增 SlideOver（抽屉）组件
4. 新增 Skeleton 骨架屏组件
5. 统一 Input/Select/Textarea 样式
6. 统一间距系统

### Phase 3: 页面级改造（3-5 天）

1. MonitorPage 重构：StatCard 概览 + DataTable + 告警时间线
2. WatchlistPage 重构：DataTable + 实时行情 + 可折叠筛选
3. SchedulePage 重构：StatCard 概览 + DataTable + 下次执行倒计时
4. PortfolioPage 优化：Summary Bar + DataTable
5. BacktestPage 优化：Equity Curve + StatCard 指标

### Phase 4: 细节打磨（1-2 天）

1. 所有页面添加 Skeleton 加载态
2. 所有列表页面添加专属空状态
3. 统一动画时长和缓动函数
4. 侧边栏改版（分组 + 展开宽度调整）
5. 响应式适配测试

---

*预计总工期：7-12 天*
*建议优先级：Phase 1 → Phase 3（Monitor/Watchlist）→ Phase 2 → Phase 3（其余）→ Phase 4*

---

*文档版本：v1.0*
*创建日期：2026-04-04*

### 5.3 Button 精简（5 个变体）

| 变体 | 用途 | 样式 |
|------|------|------|
| `primary` | 主要操作（提交、确认、新建） | 实色 Cyan 背景 + 白色文字 |
| `secondary` | 次要操作（取消、返回） | 透明背景 + border + 文字色 |
| `ghost` | 轻量操作（筛选、切换） | 无边框 + hover 显示背景 |
| `danger` | 危险操作（删除、移除） | 红色背景或红色文字 |
| `icon` | 图标按钮（关闭、更多） | 圆形/方形 + 无文字 |

删除 `gradient`、`settings-primary`、`settings-secondary`、`action-primary`、`action-secondary`、`home-action-ai`、`home-action-report` 等冗余变体。

### 5.4 Card 规范

```
默认 Card:
  background: var(--bg-surface)
  border: 1px solid var(--border-default)
  border-radius: var(--radius-lg)  /* 12px */
  padding: 20px
  shadow: var(--shadow-sm)
  hover: shadow-md + border-hover

交互 Card (可点击):
  cursor: pointer
  hover: translateY(-1px) + shadow-md

选中 Card:
  border-color: var(--color-primary)
  background: hsl(var(--color-primary) / var(--alpha-subtle))
```

### 5.5 表单组件

```
Input / Select:
  height: 40px (默认) | 36px (紧凑) | 44px (大)
  border-radius: var(--radius-md)  /* 8px */
  border: 1px solid var(--border-default)
  focus: border-color var(--color-primary) + ring 2px

Label:
  font-size: 13px
  font-weight: 500
  color: var(--text-secondary)
  margin-bottom: 6px
```

### 5.6 DataTable（新增组件）

用于 Monitor、Watchlist、Schedule 等列表页面，替代当前的 Card 列表：

```
DataTable:
  header: bg-surface, text-muted, font-size 12px, uppercase
  row: border-bottom 1px, hover bg-hover
  cell padding: px-4 py-3
  排序指示器: 箭头图标
  状态列: StatusDot (绿/黄/红/灰)
  操作列: icon button group
```

### 5.7 StatusDot（新增组件）

```
尺寸: 8px 圆形
颜色:
  active/online:  var(--color-success) + pulse 动画
  warning:        var(--color-warning)
  error/offline:  var(--color-danger)
  idle/disabled:  var(--text-muted)
```

---

## 六、页面级设计建议

### 6.1 首页 (/) — 微调

当前完成度高，主要优化：
- 将页面级 CSS 变量（`--home-*` 约 50 个）迁移到统一设计令牌
- Stock Pool 列表增加迷你 sparkline（7 日走势）
- 分析历史列表增加涨跌色标识

### 6.2 问股 (/chat) — 微调

- 统一消息气泡的圆角和间距
- 代码块使用统一的 syntax highlight 主题
- 将 `--chat-*` 变量迁移到统一令牌

### 6.3 持仓 (/portfolio) — 中度优化

- 顶部增加 Portfolio Summary Bar：总资产、日盈亏（带涨跌色）、总收益率
- 持仓列表改为 DataTable，增加列：当前价、成本价、盈亏额、盈亏率（带涨跌色）
- 饼图配色使用设计令牌
- 交易记录增加买卖方向色彩标识（买入 `--stock-up`，卖出 `--stock-down`）

### 6.4 监控 (/monitor) — 重点改造

当前仅基础 CRUD 列表，缺乏实时监控的视觉感受。

改造方案：

```
┌─────────────────────────────────────────────────┐
│ PageHeader: 监控中心                    [+ 新建] │
├─────────────────────────────────────────────────┤
│ 监控概览 (StatCard x3)                           │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│ │ 活跃任务  │ │ 今日告警  │ │  触发率   │         │
│ │    12    │ │    5     │ │   42%    │         │
│ └──────────┘ └──────────┘ └──────────┘         │
├────────────────────────┬────────────────────────┤
│ 监控任务列表 (DataTable) │ 告警时间线 (Timeline)   │
│ 股票 | 条件 | 间隔 |状态 │ ● 14:32 600519 触发   │
│ ──────────────────── │ ● 14:15 000858 触发   │
│ 600519 | MA5>MA20    │ ● 13:48 601318 触发   │
│         | 15min | 🟢 │                        │
│ 000858 | RSI<30      │                        │
│         | 30min | 🟢 │                        │
└────────────────────────┴────────────────────────┘
```

具体改动：
- 顶部 3 个 StatCard：活跃任务数、今日告警数、告警触发率
- 任务列表从 Card 改为 DataTable，增加 StatusDot、最后检查时间、下次检查倒计时
- 右侧增加告警时间线，按时间倒序，每条带股票名称 + 触发条件 + 触发值
- 新建表单改为 SlideOver（右侧滑出面板），而非内嵌展开

### 6.5 自选股 (/watchlist) — 重点改造

改造方案：

```
┌─────────────────────────────────────────────────┐
│ PageHeader: 自选股                [筛选] [+ 添加] │
├─────────────────────────────────────────────────┤
│ 标签栏: [全部(28)] [重点(8)] [观望(12)] [+标签]   │
├─────────────────────────────────────────────────┤
│ DataTable                                        │
│ 代码   | 名称   | 现价   | 涨跌幅 | 标签 | 操作  │
│ ─────────────────────────────────────────────── │
│ 600519 | 贵州茅台| 1856.0 | +2.3%  | 重点 | ···  │
│ 000858 | 五粮液 | 156.8  | -1.2%  | 白酒 | ···  │
│ 601318 | 中国平安| 48.5   | +0.5%  | 金融 | ···  │
└─────────────────────────────────────────────────┘
```

具体改动：
- 从 Card 列表改为 DataTable，增加实时行情列（现价、涨跌幅、涨跌额）
- 涨跌幅使用 `--stock-up` / `--stock-down` 着色
- 增加标签分组 Tab 栏，按标签快速筛选
- 条件筛选改为 SlideOver 面板
- 每行增加迷你 sparkline（可选）

### 6.6 定时任务 (/schedule) — 重点改造

改造方案：

```
┌─────────────────────────────────────────────────┐
│ PageHeader: 定时任务                    [+ 新建] │
├─────────────────────────────────────────────────┤
│ 概览 (StatCard x3)                               │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│ │ 活跃任务  │ │ 今日执行  │ │ 下次执行  │         │
│ │    5     │ │    3     │ │ 14:30    │         │
│ └──────────┘ └──────────┘ └──────────┘         │
├─────────────────────────────────────────────────┤
│ DataTable                                        │
│ 名称 | 类型 | 频率 | 上次执行 | 下次执行 | 状态   │
│ ──────────────────────────────────────────────  │
│ 每日分析 | 定时 | 每天 09:30 | 今天 09:30 ✓ | 明天│
│ 周报汇总 | 定时 | 每周五 15:00| 上周五 ✓  | 本周五│
└─────────────────────────────────────────────────┘
```

具体改动：
- 顶部 StatCard 概览
- 列表改为 DataTable，增加执行状态（成功 ✓ / 失败 ✗ / 运行中 ⟳）
- 增加"上次执行结果"列，失败时显示错误摘要
- 新建表单改为 SlideOver

### 6.7 回测 (/backtest) — 中度优化

- 回测结果增加关键指标卡片：年化收益率、最大回撤、夏普比率、胜率
- 收益曲线图使用 `--stock-up` / `--stock-down` 着色
- 将 `--backtest-*` 变量迁移到统一令牌

### 6.8 设置 (/settings) — 轻度优化

- 将 `--settings-*` 变量迁移到统一令牌
- 表单布局统一使用 Section Card 分组

---

## 七、交互优化

### 7.1 加载状态

```
页面级加载:  全屏 Skeleton Screen（骨架屏），模拟最终布局形状
列表加载:    3-5 行 Skeleton Row
按钮加载:    Spinner 替换文字 + disabled 态
数据刷新:    顶部细线进度条（类似 YouTube）
```

### 7.2 空状态

```
统一 EmptyState 组件:
  - 64px 线性插图图标（非实色）
  - 标题: 16px, text-primary
  - 描述: 14px, text-secondary
  - CTA 按钮: primary variant
  - 示例: "暂无监控任务 — 创建你的第一个监控，实时追踪技术指标变化 [+ 新建监控]"
```

### 7.3 动画规范

```
过渡时长:
  instant:  100ms  — hover 色彩变化
  fast:     150ms  — 按钮状态、tooltip
  normal:   200ms  — 面板展开、tab 切换
  slow:     300ms  — 页面过渡、drawer 滑入

缓动函数:
  默认: cubic-bezier(0.4, 0, 0.2, 1)
  弹性: cubic-bezier(0.34, 1.56, 0.64, 1)  — 用于 popover/dropdown
```

### 7.4 SlideOver 面板（新增）

用于新建/编辑表单，替代当前的内嵌展开：

```
位置: 右侧滑入
宽度: 420px (sm) | 560px (lg)
背景: var(--bg-elevated)
遮罩: hsl(0 0% 0% / 0.5) + backdrop-blur-sm
动画: translateX(100%) → translateX(0), 300ms
```

---

## 八、数据可视化

### 8.1 图表配色

```css
/* 图表专用色板 — 8 色，确保色盲友好 */
--chart-1: hsl(193 90% 45%);   /* Cyan — 主系列 */
--chart-2: hsl(247 80% 64%);   /* Purple — 次系列 */
--chart-3: hsl(37 90% 50%);    /* Amber */
--chart-4: hsl(152 65% 40%);   /* Emerald */
--chart-5: hsl(340 75% 55%);   /* Rose */
--chart-6: hsl(210 80% 55%);   /* Blue */
--chart-7: hsl(25 90% 55%);    /* Orange */
--chart-8: hsl(280 65% 55%);   /* Violet */
```

### 8.2 Sparkline（新增迷你图表）

```
尺寸: 80px × 24px
线宽: 1.5px
颜色: 根据涨跌自动选择 --stock-up / --stock-down
数据: 最近 7 个交易日收盘价
用途: 自选股列表、持仓列表、监控列表
```

### 8.3 金融数据格式化

```
涨跌幅: +2.35% (红色) / -1.28% (绿色) / 0.00% (灰色)
价格:   ¥1,856.00 (A股) / $185.60 (美股) / HK$156.80 (港股)
成交量: 1.2亿 / 3,456万
市值:   1.2万亿 / 856亿
```

---

## 九、实施路线图

### Phase 1: 设计基础 (1-2 周)

**目标**：统一设计令牌，不改变页面外观

1. 精简 CSS 变量：将 `--home-*`、`--settings-*`、`--login-*`、`--chat-*`、`--backtest-*` 等页面级变量迁移到统一的语义化令牌
2. 统一圆角：Card → `rounded-lg`(12px)，Dialog → `rounded-xl`(16px)，Button → `rounded-lg`(12px)
3. 精简阴影：从 10+ 种减少到 3 档（sm/md/lg）
4. 统一透明度：引入 5 档 alpha 阶梯
5. 添加金融色彩变量：`--stock-up`、`--stock-down`、`--stock-flat`
6. Button 变体从 12 个精简到 5 个

**涉及文件**：
- `apps/dsa-web/src/index.css`
- `apps/dsa-web/tailwind.config.js`
- `apps/dsa-web/src/components/common/Button.tsx`
- `apps/dsa-web/src/components/common/Card.tsx`

### Phase 2: 核心组件 (1-2 周)

**目标**：新增通用组件，为页面改造做准备

1. 新增 DataTable 组件（排序、状态列、操作列）
2. 新增 StatusDot 组件
3. 新增 SlideOver 面板组件
4. 新增 Sparkline 迷你图表组件
5. 新增 Skeleton 骨架屏组件
6. 优化 EmptyState 组件（统一插图风格）
7. 优化 StatCard 组件（支持趋势箭头、涨跌色）

**涉及文件**：
- `apps/dsa-web/src/components/common/DataTable.tsx` (新增)
- `apps/dsa-web/src/components/common/StatusDot.tsx` (新增)
- `apps/dsa-web/src/components/common/SlideOver.tsx` (新增)
- `apps/dsa-web/src/components/common/Sparkline.tsx` (新增)
- `apps/dsa-web/src/components/common/Skeleton.tsx` (新增)
- `apps/dsa-web/src/components/common/EmptyState.tsx` (优化)
- `apps/dsa-web/src/components/common/StatCard.tsx` (优化)

### Phase 3: 页面改造 (2-3 周)

**目标**：逐页升级，优先改造完成度低的页面

1. **MonitorPage** — StatCard 概览 + DataTable + 告警时间线 + SlideOver 新建
2. **WatchlistPage** — 标签分组 + DataTable（含行情列）+ SlideOver 筛选
3. **SchedulePage** — StatCard 概览 + DataTable（含执行状态）+ SlideOver 新建
4. **PortfolioPage** — Summary Bar + DataTable 持仓列表 + 涨跌色
5. **BacktestPage** — 指标卡片 + 图表配色优化
6. **SidebarNav** — 展开态 224px + 分组 + 描述文字
7. **HomePage / ChatPage / SettingsPage** — 迁移到统一令牌，微调

**涉及文件**：
- `apps/dsa-web/src/pages/MonitorPage.tsx`
- `apps/dsa-web/src/pages/WatchlistPage.tsx`
- `apps/dsa-web/src/pages/SchedulePage.tsx`
- `apps/dsa-web/src/pages/PortfolioPage.tsx`
- `apps/dsa-web/src/pages/BacktestPage.tsx`
- `apps/dsa-web/src/components/layout/SidebarNav.tsx`

---

*方案版本：v1.0*
*日期：2026-04-04*
*状态：待讨论确认*

---

## 八、数据可视化规范

### 8.1 图表配色

```css
/* 图表系列色（按顺序使用） */
--chart-1: hsl(193 90% 45%);   /* Cyan — 主系列 */
--chart-2: hsl(247 80% 64%);   /* Purple — 次系列 */
--chart-3: hsl(37 90% 50%);    /* Amber */
--chart-4: hsl(152 65% 40%);   /* Emerald */
--chart-5: hsl(340 75% 55%);   /* Rose */
--chart-6: hsl(210 80% 55%);   /* Blue */

/* 涨跌专用 */
--chart-up:   var(--stock-up);    /* 红色 K 线/柱 */
--chart-down: var(--stock-down);  /* 绿色 K 线/柱 */
```

### 8.2 Sparkline（迷你走势图）

```
尺寸: 80px × 24px (列表内) | 120px × 32px (卡片内)
线宽: 1.5px
颜色: 上涨用 --stock-up，下跌用 --stock-down
填充: 线色 / 0.1 的渐变填充
无坐标轴、无标签、无网格
```

### 8.3 Recharts 统一配置

```typescript
const CHART_THEME = {
  // 网格
  grid: { stroke: 'var(--border-default)', strokeDasharray: '3 3' },
  // 坐标轴
  axis: { stroke: 'var(--text-muted)', fontSize: 11 },
  // Tooltip
  tooltip: {
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border-default)',
    borderRadius: 8,
    fontSize: 13,
  },
  // 图例
  legend: { fontSize: 12, color: 'var(--text-secondary)' },
};
```

---

## 九、实施路线图

### Phase 1: 设计基础 (1-2 天)

**目标**：统一设计令牌，不改变页面外观

1. 精简 `index.css` 中的 CSS 变量
   - 删除所有页面级专属变量（`--home-*`、`--settings-*`、`--login-*`、`--chat-*`、`--backtest-*`）
   - 替换为统一的语义化令牌（`--bg-*`、`--text-*`、`--border-*`、`--shadow-*`）
   - 新增 `--stock-up`、`--stock-down`、`--stock-flat` 涨跌色变量
   - 统一透明度为 5 档阶梯

2. 更新 `tailwind.config.js`
   - 统一圆角为 4 档
   - 精简阴影为 3 档
   - 添加图表色和涨跌色

3. 精简 Button 组件
   - 从 12 个变体减少到 5 个
   - 更新所有页面的 Button 引用

**验证**：所有页面视觉无明显变化，功能正常

### Phase 2: 核心组件 (2-3 天)

**目标**：新增/升级共享组件

1. 新增 `DataTable` 组件 — 可排序、可筛选的表格
2. 新增 `StatusDot` 组件 — 状态指示灯
3. 新增 `SlideOver` 组件 — 右侧滑出面板
4. 新增 `Sparkline` 组件 — 迷你走势图
5. 升级 `StatCard` 组件 — 增加趋势箭头和迷你图表
6. 升级 `EmptyState` 组件 — 统一插图风格
7. 新增 `Skeleton` 组件 — 骨架屏加载态

**验证**：组件 Storybook 或独立页面预览

### Phase 3: 页面改造 (3-5 天)

**目标**：逐页升级，优先改造完成度低的页面

1. **MonitorPage** — StatCard 概览 + DataTable + 告警时间线 + SlideOver 新建
2. **WatchlistPage** — 标签分组 + DataTable（含行情列）+ SlideOver 筛选
3. **SchedulePage** — StatCard 概览 + DataTable（含执行状态）+ SlideOver 新建
4. **PortfolioPage** — Summary Bar + DataTable 持仓列表 + 涨跌色
5. **BacktestPage** — 指标卡片 + 图表配色统一
6. **HomePage** — 迁移到统一令牌 + sparkline
7. **ChatPage** — 迁移到统一令牌
8. **SettingsPage** — 迁移到统一令牌

**验证**：每个页面改造后进行功能回归测试

### Phase 4: 布局升级 (1-2 天)

**目标**：侧边栏和全局布局优化

1. 侧边栏扩展为 224px，增加分组和描述
2. 统一页面间距系统
3. 响应式断点优化
4. 移动端 drawer 导航优化

**验证**：多设备/多分辨率测试

---

## 十、总结

本方案的核心思路是**做减法**：

- CSS 变量从 200+ 精简到 60 个左右
- Button 变体从 12 个减少到 5 个
- 阴影从 10+ 种减少到 3 种
- 圆角从 6 档减少到 4 档
- 透明度从随意值统一为 5 档

同时**做加法**的地方：

- 新增 DataTable、SlideOver、Sparkline、StatusDot、Skeleton 等金融场景组件
- 新增 A 股涨跌色语义变量
- Monitor/Watchlist/Schedule 三个页面从基础 CRUD 升级为专业工作台
- 统一的数据可视化配色方案

预计总工期 7-12 天，可按 Phase 分批交付，每个 Phase 独立可验证。

---

*方案版本：v1.0*
*日期：2026-04-04*

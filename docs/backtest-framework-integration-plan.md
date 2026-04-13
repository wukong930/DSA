# DSA 回测框架集成方案

> 日期：2026-04-11
> 状态：方案评审

---

## 一、背景与目标

### 现状

DSA 当前的回测系统（`BacktestEngine`）定位是 **AI 建议验证器**：

- 固定逻辑：拿 AI 操作建议 + 止损止盈，对比后续行情判断对错
- 仅支持日线 OHLC 数据（`StockDaily` 表）
- Long-only 模拟，无因子、无组合、无自定义策略
- 无外部数据接入口

### 目标

在保留现有 AI 验证回测的基础上，集成通用回测框架，支持：

1. **自定义因子** — 用户可编写技术/基本面/另类因子
2. **外部数据包接入** — 支持导入用户购买的高频、分钟线、财务等数据
3. **自定义策略** — 基于因子信号的买卖策略
4. **完整回测指标** — 夏普比率、最大回撤、年化收益等

---

## 二、框架选型

### 候选对比

| 维度 | backtrader | vnpy | zipline-reloaded |
|------|-----------|------|-----------------|
| 定位 | 纯回测框架 | 量化交易平台（回测+实盘） | 回测+因子研究 |
| 自定义因子 | Indicator 体系，灵活 | 有限 | Pipeline API，强 |
| 自定义数据源 | DataFeed 抽象，易扩展 | 需适配 Gateway | Bundle 机制，较重 |
| 学习曲线 | 中等 | 高（全栈平台） | 高（Quantopian 遗产） |
| 维护状态 | 社区维护，稳定 | 活跃 | 社区 fork，一般 |
| 依赖体量 | 轻量（纯 Python） | 重（C++ 扩展、Qt） | 中等 |
| A 股支持 | 需自行适配数据源 | 原生支持 | 需自行适配 |
| 与 DSA 集成难度 | 低 | 高 | 中 |

### 推荐：backtrader

理由：

1. **轻量** — 纯 Python，不引入 Qt/C++ 依赖，与 DSA 的 Docker 部署兼容
2. **DataFeed 抽象好** — 可以直接对接 DSA 现有的 `DataFetcherManager` 和外部数据包
3. **Indicator 体系成熟** — 内置 100+ 技术指标，支持自定义因子
4. **Strategy 类清晰** — `next()` 方法驱动，易于理解和扩展
5. **Analyzer 丰富** — 夏普、回撤、交易统计等开箱即用
6. **社区资源多** — 文档完善，A 股适配案例丰富

---

## 三、架构设计

### 整体分层

```
┌─────────────────────────────────────────────────┐
│                   Web / API                      │
│  (现有 BacktestPage + 新增策略回测页面)            │
├─────────────────────────────────────────────────┤
│              API Layer (FastAPI)                  │
│  /api/v1/backtest/*        现有 AI 验证回测        │
│  /api/v1/strategy-bt/*     新增 策略回测           │
├─────────────────────────────────────────────────┤
│            Service Layer                         │
│  BacktestService           现有，不动              │
│  StrategyBacktestService   新增，编排 backtrader   │
├─────────────────────────────────────────────────┤
│            Engine Layer                          │
│  BacktestEngine            现有 AI 验证引擎        │
│  BtEngineAdapter           新增 backtrader 适配    │
├─────────────────────────────────────────────────┤
│            Data Layer                            │
│  DataFetcherManager        现有数据源              │
│  ExternalDataLoader        新增 外部数据包加载      │
│  BtDataFeed                新增 backtrader 数据桥  │
├─────────────────────────────────────────────────┤
│            Storage                               │
│  StockDaily                现有日线表              │
│  ExternalDataset           新增 外部数据集元信息    │
│  StrategyBacktestResult    新增 策略回测结果        │
└─────────────────────────────────────────────────┘
```

### 核心原则

- **不改现有回测** — AI 验证回测（`BacktestEngine` + `BacktestService`）保持不动
- **并行新增** — 策略回测作为独立模块，共享数据层
- **数据桥接** — 通过适配器将 DSA 数据源和外部数据包转为 backtrader DataFeed

---

## 四、模块设计

### 4.1 外部数据包加载（ExternalDataLoader）

```
src/data/
├── external_loader.py      # 外部数据包加载器
├── dataset_registry.py     # 数据集注册与元信息管理
└── formats/
    ├── csv_loader.py       # CSV 格式
    ├── parquet_loader.py   # Parquet 格式
    └── hdf5_loader.py      # HDF5 格式
```

职责：
- 支持 CSV / Parquet / HDF5 三种常见数据包格式
- 统一输出为 pandas DataFrame，列名标准化
- 数据集注册：记录名称、路径、字段映射、时间范围
- 数据校验：检查必要字段、时间连续性、缺失值

配置方式（`.env`）：
```
EXTERNAL_DATA_DIR=/path/to/data_packages
```

数据集注册示例（`data_packages/manifest.yaml`）：
```yaml
datasets:
  - name: "分钟线数据"
    path: "minute_bars/"
    format: parquet
    frequency: 1min
    columns:
      datetime: datetime
      open: open
      high: high
      low: low
      close: close
      volume: vol
    stocks: ["600519", "000001"]
    date_range: ["2020-01-01", "2025-12-31"]

  - name: "财务因子数据"
    path: "fundamental_factors.parquet"
    format: parquet
    frequency: quarterly
    columns:
      date: report_date
      code: stock_code
      pe_ttm: pe_ttm
      pb: pb
      roe: roe
```

### 4.2 Backtrader 数据桥（BtDataFeed）

```
src/backtest_bt/
├── __init__.py
├── feeds.py                # DataFeed 适配器
├── indicators.py           # 自定义因子注册
├── strategies.py           # 策略基类 + 内置策略
├── analyzers.py            # 自定义分析器
├── engine.py               # backtrader 引擎封装
└── results.py              # 结果解析与存储
```

`feeds.py` 提供两个 DataFeed：

1. **DSADataFeed** — 桥接 DSA 现有数据源
   - 从 `StockDaily` 表或 `DataFetcherManager` 获取日线
   - 自动转为 backtrader 的 OHLCV 格式

2. **ExternalDataFeed** — 桥接外部数据包
   - 从 `ExternalDataLoader` 加载数据
   - 支持任意频率（日线、分钟线、Tick）
   - 支持附加自定义列（因子列）

### 4.3 自定义因子（Indicators）

backtrader 的 Indicator 体系天然支持自定义因子：

```python
# 用户自定义因子示例
import backtrader as bt

class MomentumFactor(bt.Indicator):
    """动量因子：N日收益率"""
    params = (('period', 20),)
    lines = ('momentum',)

    def __init__(self):
        self.lines.momentum = (self.data.close / self.data.close(-self.p.period)) - 1.0


class PEFactor(bt.Indicator):
    """PE 因子：从外部数据列读取"""
    lines = ('pe',)

    def __init__(self):
        self.lines.pe = self.data.pe_ttm  # 外部数据包中的列
```

因子注册机制：

```
data_packages/factors/
├── momentum.py
├── value.py
└── custom_factor.py
```

系统启动时扫描 `factors/` 目录，自动注册到因子库。用户也可通过 API 上传因子脚本。

### 4.4 策略定义

```python
# 内置策略基类
class DSAStrategy(bt.Strategy):
    """DSA 策略基类，提供便捷方法"""

    def log_trade(self, order):
        """统一交易日志"""
        ...

    def get_factor(self, name):
        """获取已注册因子的值"""
        ...


# 用户自定义策略示例
class DualMomentumStrategy(DSAStrategy):
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('pe_threshold', 30),
    )

    def __init__(self):
        self.fast_mom = MomentumFactor(self.data, period=self.p.fast_period)
        self.slow_mom = MomentumFactor(self.data, period=self.p.slow_period)
        self.pe = PEFactor(self.data)  # 来自外部数据包

    def next(self):
        if not self.position:
            if self.fast_mom > self.slow_mom and self.pe < self.p.pe_threshold:
                self.buy()
        else:
            if self.fast_mom < self.slow_mom:
                self.sell()
```

### 4.5 引擎封装（BtEngineAdapter）

```python
class BtEngineAdapter:
    """封装 backtrader Cerebro，提供 DSA 风格的调用接口"""

    def run(
        self,
        stock_codes: list[str],
        strategy_class: type,
        strategy_params: dict,
        start_date: str,
        end_date: str,
        data_source: str = "internal",  # "internal" | "external"
        dataset_name: str | None = None,
        initial_cash: float = 100_000,
        commission: float = 0.001,
        slippage: float = 0.001,
    ) -> StrategyBacktestResult:
        ...
```

返回结构：
```python
@dataclass
class StrategyBacktestResult:
    # 基本信息
    strategy_name: str
    stock_codes: list[str]
    start_date: str
    end_date: str
    data_source: str

    # 收益指标
    total_return_pct: float
    annual_return_pct: float
    benchmark_return_pct: float  # 基准（买入持有）收益

    # 风险指标
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    volatility_annual: float
    calmar_ratio: float

    # 交易统计
    total_trades: int
    win_rate: float
    profit_loss_ratio: float
    avg_holding_days: float

    # 逐日净值曲线（供前端绘图）
    equity_curve: list[dict]  # [{date, equity, benchmark, drawdown}]

    # 交易明细
    trade_log: list[dict]  # [{date, action, price, size, pnl, reason}]
```

### 4.6 数据库扩展

新增两张表：

```python
class ExternalDataset(Base):
    """外部数据集注册信息"""
    __tablename__ = 'external_datasets'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    description = Column(Text)
    file_path = Column(String(500))
    format = Column(String(20))        # csv / parquet / hdf5
    frequency = Column(String(20))     # 1min / 5min / daily / quarterly
    column_mapping = Column(JSON)      # 字段映射
    date_range_start = Column(Date)
    date_range_end = Column(Date)
    stock_codes = Column(JSON)         # 覆盖的股票列表
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class StrategyBacktestRun(Base):
    """策略回测运行记录"""
    __tablename__ = 'strategy_backtest_runs'

    id = Column(Integer, primary_key=True)
    strategy_name = Column(String(100))
    strategy_params = Column(JSON)
    stock_codes = Column(JSON)
    data_source = Column(String(50))
    dataset_name = Column(String(100), nullable=True)
    start_date = Column(Date)
    end_date = Column(Date)
    initial_cash = Column(Float)

    # 结果指标
    total_return_pct = Column(Float)
    annual_return_pct = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown_pct = Column(Float)
    win_rate = Column(Float)
    total_trades = Column(Integer)

    # 详细数据（JSON 存储）
    equity_curve = Column(JSON)
    trade_log = Column(JSON)

    created_at = Column(DateTime)
```

### 4.7 API 端点

```
POST   /api/v1/strategy-bt/run              运行策略回测
GET    /api/v1/strategy-bt/runs              回测历史列表
GET    /api/v1/strategy-bt/runs/{id}         回测详情（含净值曲线）
DELETE /api/v1/strategy-bt/runs/{id}         删除回测记录

GET    /api/v1/strategy-bt/strategies        可用策略列表
POST   /api/v1/strategy-bt/strategies        上传自定义策略（Python 脚本）

GET    /api/v1/strategy-bt/factors           可用因子列表
POST   /api/v1/strategy-bt/factors           上传自定义因子

GET    /api/v1/datasets                      已注册数据集列表
POST   /api/v1/datasets                      注册外部数据集
DELETE /api/v1/datasets/{id}                 移除数据集
```

---

## 五、前端扩展

### 新增页面：策略回测

```
apps/dsa-web/src/
├── pages/
│   └── StrategyBacktestPage.tsx        # 策略回测主页面
├── components/strategy-backtest/
│   ├── BacktestConfigPanel.tsx         # 左侧：策略选择、参数配置、数据源选择
│   ├── EquityCurveChart.tsx            # 净值曲线图（echarts/recharts）
│   ├── MetricsGrid.tsx                 # 指标卡片网格
│   ├── TradeLogTable.tsx               # 交易明细表
│   └── DrawdownChart.tsx               # 回撤曲线图
├── stores/
│   └── strategyBacktestStore.ts        # Zustand store
└── api/
    └── strategyBacktest.ts             # API 调用
```

### 页面布局

```
┌──────────────────────────────────────────────────┐
│  策略回测                                         │
├────────────┬─────────────────────────────────────┤
│ 配置面板    │  结果展示区                           │
│            │                                      │
│ 策略选择    │  ┌─────────┬─────────┬──────────┐   │
│ 参数调整    │  │年化收益   │夏普比率  │最大回撤    │   │
│ 股票范围    │  └─────────┴─────────┴──────────┘   │
│ 数据源选择  │                                      │
│ 时间范围    │  ┌──────────────────────────────┐   │
│            │  │      净值曲线 + 基准对比        │   │
│ [运行回测]  │  └──────────────────────────────┘   │
│            │                                      │
│ 历史记录    │  ┌──────────────────────────────┐   │
│  · 记录1   │  │        回撤曲线               │   │
│  · 记录2   │  └──────────────────────────────┘   │
│  · ...     │                                      │
│            │  ┌──────────────────────────────┐   │
│            │  │      交易明细表               │   │
│            │  └──────────────────────────────┘   │
└────────────┴─────────────────────────────────────┘
```

---

## 六、实施计划

### Phase 1：数据基础（约 1 周）

| 任务 | 文件 | 说明 |
|------|------|------|
| 外部数据加载器 | `src/data/external_loader.py` | CSV/Parquet/HDF5 读取 + 标准化 |
| 数据集注册 | `src/data/dataset_registry.py` | manifest.yaml 解析 + DB 注册 |
| DB 迁移 | `src/storage.py` | 新增 `external_datasets` 表 |
| 数据集 API | `api/v1/endpoints/datasets.py` | CRUD 端点 |

### Phase 2：回测引擎集成（约 1.5 周）

| 任务 | 文件 | 说明 |
|------|------|------|
| backtrader DataFeed 适配 | `src/backtest_bt/feeds.py` | DSA 数据源 + 外部数据桥接 |
| 引擎封装 | `src/backtest_bt/engine.py` | Cerebro 封装 + 结果解析 |
| 内置策略 | `src/backtest_bt/strategies.py` | 均线交叉、动量等基础策略 |
| 因子注册 | `src/backtest_bt/indicators.py` | 因子扫描 + 注册机制 |
| DB 迁移 | `src/storage.py` | 新增 `strategy_backtest_runs` 表 |
| 策略回测 API | `api/v1/endpoints/strategy_bt.py` | 运行 + 查询端点 |

### Phase 3：前端展示（约 1.5 周）

| 任务 | 文件 | 说明 |
|------|------|------|
| 策略回测页面 | `StrategyBacktestPage.tsx` | 主页面框架 |
| 配置面板 | `BacktestConfigPanel.tsx` | 策略/参数/数据源选择 |
| 净值曲线图 | `EquityCurveChart.tsx` | echarts 折线图 |
| 指标卡片 | `MetricsGrid.tsx` | 收益/风险指标展示 |
| 交易明细 | `TradeLogTable.tsx` | 表格组件 |
| Store + API | `strategyBacktestStore.ts` | 状态管理 |

### Phase 4：打磨与安全（约 0.5 周）

| 任务 | 说明 |
|------|------|
| 策略脚本沙箱 | 用户上传的 Python 脚本需要安全隔离执行 |
| 回测任务队列 | 长时间回测异步执行，避免阻塞 API |
| 数据缓存 | 外部数据包加载结果缓存，避免重复 IO |
| 文档 | 因子编写指南、数据包格式说明、策略模板 |

---

## 七、风险与注意事项

### 安全风险

- **用户上传 Python 脚本** — 必须沙箱执行（`RestrictedPython` 或 subprocess 隔离），禁止文件系统/网络访问
- 初期可以只支持内置策略 + 参数调整，不开放脚本上传

### 性能风险

- backtrader 单线程执行，大数据量回测可能耗时较长
- 建议：回测任务异步化（Celery 或 asyncio），前端轮询进度
- 分钟线数据量大，需要分页加载或内存映射

### 兼容性

- backtrader 最后一个 PyPI 发布是 1.9.78（2023），但社区 fork `backtrader2` 持续维护
- 建议使用 `backtrader2`，兼容 Python 3.10+

### 与现有系统的关系

- 现有 AI 验证回测（`BacktestEngine`）完全不动
- 新模块独立目录 `src/backtest_bt/`、独立 API 前缀 `/api/v1/strategy-bt/`
- 共享数据层（`StockDaily` 表 + `DataFetcherManager`）

---

## 八、依赖变更

```
# requirements.txt 新增
backtrader2>=2.0.0
pyarrow>=14.0.0          # Parquet 读取
tables>=3.9.0            # HDF5 读取（可选）
```

Docker 镜像体积预估增加约 50MB。

---

## 九、替代方案备注

如果后续发现 backtrader 的 Indicator 体系不够灵活（比如需要跨股票因子、截面因子），可以考虑：

- **alphalens-reloaded** — 专门做因子分析（IC、分层收益），与 backtrader 互补
- **vectorbt** — 向量化回测，性能极高，适合大规模因子筛选，但 API 风格差异大

这两个可以作为 Phase 2 之后的增强选项，不影响初期架构。

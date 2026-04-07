/**
 * Mock data for UI prototype demo.
 * Realistic Chinese stock market examples with complete data structures.
 */

import type { MonitorTask, MonitorAlert } from '../api/monitor';
import type { WatchlistItem, FilterResult } from '../api/watchlist';
import type { ScheduledTask } from '../api/scheduler';
import type { AnalysisReport, HistoryItem, TaskInfo } from '../types/analysis';

// ============ Monitor Mock Data ============

export const MOCK_INDICATORS: string[] = [
  'sma_5', 'sma_10', 'sma_20', 'sma_60', 'sma_120', 'sma_250',
  'ema_5', 'ema_10', 'ema_20', 'ema_60',
  'macd', 'macd_signal', 'macd_hist',
  'rsi_6', 'rsi_14',
  'kdj_k', 'kdj_d', 'kdj_j',
  'boll_upper', 'boll_mid', 'boll_lower',
  'atr_14', 'obv', 'cci_14',
  'williams_r', 'roc_12', 'mfi_14',
  'adx_14', 'dmi_plus', 'dmi_minus',
  'vwap', 'volume_ratio', 'turnover_rate',
  'price', 'change_pct', 'amplitude',
  'high_52w', 'low_52w',
  'ma_trend_score', 'volatility_20',
  'support_1', 'resistance_1',
  'chip_concentration', 'profit_ratio',
];

export const MOCK_MONITOR_TASKS: MonitorTask[] = [
  {
    id: 1,
    stockCode: '600519',
    stockName: '贵州茅台',
    market: 'cn',
    conditions: [
      { indicator: 'rsi_14', op: '>', value: 70 },
      { indicator: 'macd_hist', op: '<', value: 0 },
    ],
    isActive: true,
    intervalMinutes: 15,
    lastCheckedAt: '2026-04-04T14:30:00',
    lastTriggeredAt: '2026-04-03T10:15:00',
    createdAt: '2026-03-20T09:00:00',
  },
  {
    id: 2,
    stockCode: '000858',
    stockName: '五粮液',
    market: 'cn',
    conditions: [
      { indicator: 'price', op: '<', value: 130 },
      { indicator: 'volume_ratio', op: '>', value: 2.0 },
    ],
    isActive: true,
    intervalMinutes: 30,
    lastCheckedAt: '2026-04-04T14:00:00',
    lastTriggeredAt: null,
    createdAt: '2026-03-25T10:30:00',
  },
  {
    id: 3,
    stockCode: '300750',
    stockName: '宁德时代',
    market: 'cn',
    conditions: [
      { indicator: 'sma_5', op: '>', indicator2: 'sma_20' },
      { indicator: 'macd', op: '>', value: 0 },
    ],
    isActive: true,
    intervalMinutes: 15,
    lastCheckedAt: '2026-04-04T14:30:00',
    lastTriggeredAt: '2026-04-04T09:45:00',
    createdAt: '2026-03-18T08:00:00',
  },
  {
    id: 4,
    stockCode: 'AAPL',
    stockName: 'Apple Inc.',
    market: 'us',
    conditions: [
      { indicator: 'rsi_14', op: '<', value: 30 },
    ],
    isActive: false,
    intervalMinutes: 60,
    lastCheckedAt: '2026-04-03T21:00:00',
    lastTriggeredAt: null,
    createdAt: '2026-03-15T20:00:00',
  },
  {
    id: 5,
    stockCode: 'hk00700',
    stockName: '腾讯控股',
    market: 'hk',
    conditions: [
      { indicator: 'boll_lower', op: '>', indicator2: 'price' },
      { indicator: 'kdj_j', op: '<', value: 20 },
    ],
    isActive: true,
    intervalMinutes: 15,
    lastCheckedAt: '2026-04-04T15:00:00',
    lastTriggeredAt: '2026-04-02T14:20:00',
    createdAt: '2026-03-22T11:00:00',
  },
  {
    id: 6,
    stockCode: '002594',
    stockName: '比亚迪',
    market: 'cn',
    conditions: [
      { indicator: 'change_pct', op: '>', value: 5 },
    ],
    isActive: true,
    intervalMinutes: 5,
    lastCheckedAt: '2026-04-04T14:55:00',
    lastTriggeredAt: '2026-04-01T13:30:00',
    createdAt: '2026-03-28T09:30:00',
  },
];

export const MOCK_MONITOR_ALERTS: MonitorAlert[] = [
  {
    id: 1,
    taskId: 3,
    stockCode: '300750',
    conditionMatched: { indicator: 'sma_5', op: '>', indicator2: 'sma_20', actualValues: { sma_5: 218.5, sma_20: 215.3 } },
    indicatorValues: { sma_5: 218.5, sma_20: 215.3, macd: 1.25, price: 220.8 },
    isRead: false,
    notifiedVia: 'telegram',
    createdAt: '2026-04-04T09:45:00',
  },
  {
    id: 2,
    taskId: 5,
    stockCode: 'hk00700',
    conditionMatched: { indicator: 'kdj_j', op: '<', value: 20, actualValue: 15.3 },
    indicatorValues: { kdj_k: 22.1, kdj_d: 25.8, kdj_j: 15.3, price: 388.2 },
    isRead: false,
    notifiedVia: 'feishu',
    createdAt: '2026-04-02T14:20:00',
  },
  {
    id: 3,
    taskId: 1,
    stockCode: '600519',
    conditionMatched: { indicator: 'rsi_14', op: '>', value: 70, actualValue: 73.5 },
    indicatorValues: { rsi_14: 73.5, macd_hist: -0.82, price: 1688.0 },
    isRead: true,
    notifiedVia: 'email',
    createdAt: '2026-04-03T10:15:00',
  },
  {
    id: 4,
    taskId: 6,
    stockCode: '002594',
    conditionMatched: { indicator: 'change_pct', op: '>', value: 5, actualValue: 6.28 },
    indicatorValues: { change_pct: 6.28, volume_ratio: 3.15, price: 298.5 },
    isRead: true,
    notifiedVia: 'telegram',
    createdAt: '2026-04-01T13:30:00',
  },
  {
    id: 5,
    taskId: 3,
    stockCode: '300750',
    conditionMatched: { indicator: 'macd', op: '>', value: 0, actualValue: 0.85 },
    indicatorValues: { macd: 0.85, macd_signal: 0.32, price: 215.6 },
    isRead: true,
    notifiedVia: null,
    createdAt: '2026-03-28T10:00:00',
  },
];

// ============ Watchlist Mock Data ============

export const MOCK_WATCHLIST_ITEMS: WatchlistItem[] = [
  {
    id: 1, userId: 0, stockCode: '600519', stockName: '贵州茅台', market: 'cn',
    tags: ['白酒', '核心持仓'], notes: '长期持有，关注季报', addedAt: '2026-01-15T10:00:00',
  },
  {
    id: 2, userId: 0, stockCode: '000858', stockName: '五粮液', market: 'cn',
    tags: ['白酒'], notes: '等回调到 125 以下建仓', addedAt: '2026-02-10T14:00:00',
  },
  {
    id: 3, userId: 0, stockCode: '300750', stockName: '宁德时代', market: 'cn',
    tags: ['新能源', '龙头'], notes: null, addedAt: '2026-02-20T09:30:00',
  },
  {
    id: 4, userId: 0, stockCode: '002594', stockName: '比亚迪', market: 'cn',
    tags: ['新能源', '汽车'], notes: '关注海外销量数据', addedAt: '2026-03-01T11:00:00',
  },
  {
    id: 5, userId: 0, stockCode: 'hk00700', stockName: '腾讯控股', market: 'hk',
    tags: ['互联网', '港股'], notes: '回购力度加大', addedAt: '2026-01-20T15:00:00',
  },
  {
    id: 6, userId: 0, stockCode: 'AAPL', stockName: 'Apple Inc.', market: 'us',
    tags: ['科技', '美股'], notes: 'WWDC 前观望', addedAt: '2026-03-05T22:00:00',
  },
  {
    id: 7, userId: 0, stockCode: 'NVDA', stockName: 'NVIDIA Corp.', market: 'us',
    tags: ['AI', '芯片', '美股'], notes: 'AI 算力龙头，注意估值', addedAt: '2026-02-28T21:00:00',
  },
  {
    id: 8, userId: 0, stockCode: '601318', stockName: '中国平安', market: 'cn',
    tags: ['金融', '保险'], notes: '低估值，分红稳定', addedAt: '2026-03-10T10:00:00',
  },
  {
    id: 9, userId: 0, stockCode: '000001', stockName: '平安银行', market: 'cn',
    tags: ['金融', '银行'], notes: null, addedAt: '2026-03-12T09:00:00',
  },
  {
    id: 10, userId: 0, stockCode: 'hk09988', stockName: '阿里巴巴-W', market: 'hk',
    tags: ['互联网', '港股', '电商'], notes: 'AI 云业务增长预期', addedAt: '2026-03-15T16:00:00',
  },
];

export const MOCK_FILTER_RESULTS: FilterResult[] = [
  {
    stockCode: '300750', stockName: '宁德时代',
    signals: [
      { indicator: 'rsi_14', op: '<', value: 30, actualValue: 28.5, triggered: true },
      { indicator: 'macd', op: '>', value: 0, actualValue: 0.85, triggered: true },
    ],
    indicatorSnapshot: { rsi_14: 28.5, macd: 0.85, price: 220.8, sma_20: 215.3 },
  },
  {
    stockCode: '601318', stockName: '中国平安',
    signals: [
      { indicator: 'rsi_14', op: '<', value: 30, actualValue: 25.2, triggered: true },
      { indicator: 'macd', op: '>', value: 0, actualValue: 0.12, triggered: true },
    ],
    indicatorSnapshot: { rsi_14: 25.2, macd: 0.12, price: 48.6, sma_20: 47.8 },
  },
];

// ============ Scheduler Mock Data ============

export const MOCK_SCHEDULED_TASKS: ScheduledTask[] = [
  {
    id: 1, userId: 0, taskType: 'daily_analysis', name: '白酒组合每日追踪',
    stockCodes: ['600519', '000858', '300750'],
    scheduleConfig: { type: 'daily', time: '08:30', timezone: 'Asia/Shanghai' },
    analysisMode: 'traditional',
    isActive: true,
    lastRunAt: '2026-04-04T08:30:00',
    nextRunAt: '2026-04-07T08:30:00',
    createdAt: '2026-02-01T10:00:00',
  },
  {
    id: 2, userId: 0, taskType: 'daily_analysis', name: '美股科技龙头',
    stockCodes: ['AAPL', 'NVDA'],
    scheduleConfig: { type: 'daily', time: '22:00', timezone: 'America/New_York' },
    analysisMode: 'traditional',
    isActive: true,
    lastRunAt: '2026-04-03T22:00:00',
    nextRunAt: '2026-04-04T22:00:00',
    createdAt: '2026-03-01T20:00:00',
  },
  {
    id: 3, userId: 0, taskType: 'daily_analysis', name: null,
    stockCodes: ['hk00700', 'hk09988'],
    scheduleConfig: { type: 'workday', time: '09:00', timezone: 'Asia/Hong_Kong' },
    analysisMode: 'agent',
    isActive: true,
    lastRunAt: '2026-04-04T09:00:00',
    nextRunAt: '2026-04-07T09:00:00',
    createdAt: '2026-03-10T11:00:00',
  },
  {
    id: 4, userId: 0, taskType: 'daily_analysis', name: null,
    stockCodes: ['002594', '601318', '000001'],
    scheduleConfig: { type: 'interval', intervalMinutes: 120 },
    analysisMode: 'traditional',
    isActive: false,
    lastRunAt: '2026-04-02T14:00:00',
    nextRunAt: null,
    createdAt: '2026-03-20T09:00:00',
  },
];

// ============ History & Report Mock Data ============

export const MOCK_HISTORY_ITEMS: HistoryItem[] = [
  {
    id: 1, queryId: 'q-001', stockCode: '600519', stockName: '贵州茅台',
    reportType: 'detailed', sentimentScore: 72, operationAdvice: '持有观望，等待回调加仓',
    createdAt: '2026-04-04T08:35:00',
  },
  {
    id: 2, queryId: 'q-002', stockCode: '300750', stockName: '宁德时代',
    reportType: 'detailed', sentimentScore: 65, operationAdvice: '短线可关注突破信号',
    createdAt: '2026-04-04T08:36:00',
  },
  {
    id: 3, queryId: 'q-003', stockCode: '000858', stockName: '五粮液',
    reportType: 'detailed', sentimentScore: 55, operationAdvice: '中性偏弱，建议观望',
    createdAt: '2026-04-04T08:37:00',
  },
  {
    id: 4, queryId: 'q-004', stockCode: 'NVDA', stockName: 'NVIDIA Corp.',
    reportType: 'full', sentimentScore: 82, operationAdvice: '强势上涨趋势，可持有',
    createdAt: '2026-04-03T22:05:00',
  },
  {
    id: 5, queryId: 'q-005', stockCode: 'hk00700', stockName: '腾讯控股',
    reportType: 'detailed', sentimentScore: 68, operationAdvice: '回购支撑，逢低布局',
    createdAt: '2026-04-04T09:05:00',
  },
  {
    id: 6, queryId: 'q-006', stockCode: '002594', stockName: '比亚迪',
    reportType: 'simple', sentimentScore: 75, operationAdvice: '趋势向好，可适量加仓',
    createdAt: '2026-04-03T14:10:00',
  },
  {
    id: 7, queryId: 'q-007', stockCode: 'AAPL', stockName: 'Apple Inc.',
    reportType: 'detailed', sentimentScore: 60, operationAdvice: '横盘整理，等待方向选择',
    createdAt: '2026-04-03T22:08:00',
  },
  {
    id: 8, queryId: 'q-008', stockCode: '601318', stockName: '中国平安',
    reportType: 'simple', sentimentScore: 58, operationAdvice: '估值偏低，长线可配置',
    createdAt: '2026-04-02T08:40:00',
  },
];

export const MOCK_REPORT_MAOTAI: AnalysisReport = {
  meta: {
    id: 1, queryId: 'q-001', stockCode: '600519', stockName: '贵州茅台',
    reportType: 'detailed', reportLanguage: 'zh',
    createdAt: '2026-04-04T08:35:00', currentPrice: 1688.0, changePct: 1.25,
    modelUsed: 'gemini-2.0-flash',
  },
  summary: {
    analysisSummary: `## 贵州茅台（600519）技术分析报告

### 一句话结论
**看多** — 建议仓位 60%

茅台当前处于中期上升趋势中，均线多头排列，MACD 金叉后持续放量，RSI 进入强势区间但尚未超买。短期受白酒板块轮动带动，量价配合良好。

### 技术面分析

**趋势判断：上升趋势**
- MA5(1685) > MA10(1672) > MA20(1658) > MA60(1620)，均线多头排列
- MACD(2.35) 位于零轴上方，红柱持续放大
- 布林带开口扩大，价格沿上轨运行

**动量指标**
- RSI(14) = 73.5，进入强势区间，接近超买但未触发
- KDJ：K=78.2, D=72.1, J=90.4，高位运行
- CCI(14) = 125，强势

**量价关系**
- 近5日成交量均值较20日均量放大 35%
- OBV 持续上升，资金持续流入
- 换手率 0.82%，活跃度适中

### 筹码分析
- 获利盘比例：89.2%
- 成本集中度(90%)：1580-1720
- 套牢盘主要分布在 1750-1800 区间

### 基本面速览
- PE(TTM): 28.5 | PB: 9.8
- 净利润增速(YoY): 15.2%
- 机构持仓占比: 82.3%
- 北向资金近5日净买入: +8.2亿`,
    operationAdvice: '持有观望，等待回调加仓',
    trendPrediction: '短期看涨，目标位 1720-1750',
    sentimentScore: 72,
    sentimentLabel: '乐观',
  },
  strategy: {
    idealBuy: '1650-1660（MA20 附近）',
    secondaryBuy: '1620-1630（MA60 支撑）',
    stopLoss: '1580（跌破布林中轨）',
    takeProfit: '1750（前高压力位）',
  },
  details: {
    newsContent: `**近期重要新闻：**
1. 贵州茅台2025年年报：营收同比增长16.2%，净利润同比增长15.2%，超市场预期
2. 茅台冰淇淋全国门店突破100家，年轻化战略持续推进
3. 飞天茅台批价稳定在2750-2800元，渠道库存处于低位
4. 白酒板块近期获北向资金持续加仓，茅台为主要标的`,
    belongBoards: [
      { name: '白酒', code: 'BK0477', type: 'industry' },
      { name: '贵州板块', code: 'BK0480', type: 'region' },
      { name: '沪股通', code: 'BK0707', type: 'concept' },
    ],
    sectorRankings: {
      top: [
        { name: '白酒', changePct: 2.85 },
        { name: '食品饮料', changePct: 1.92 },
        { name: '消费', changePct: 1.45 },
      ],
      bottom: [
        { name: '光伏', changePct: -2.15 },
        { name: '锂电池', changePct: -1.88 },
      ],
    },
  },
};

export const MOCK_ACTIVE_TASKS: TaskInfo[] = [];

// ============ Flag ============

/** Set to true to use mock data instead of API calls */
export const USE_MOCK = false;

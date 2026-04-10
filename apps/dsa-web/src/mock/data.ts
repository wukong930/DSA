/**
 * Mock data for UI prototype demo.
 * Realistic Chinese stock market examples with complete data structures.
 */

import type { MonitorTask, MonitorAlert } from '../api/monitor';
import type { WatchlistItem, FilterResult } from '../api/watchlist';
import type { ScheduledTask } from '../api/scheduler';
import type { AnalysisReport, HistoryItem, HistoryGroupItem, TaskInfo } from '../types/analysis';
import type { SkillInfo, ChatSessionItem } from '../api/agent';
import type { SystemConfigItem } from '../types/systemConfig';

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
    runStatus: 'idle', failureCount: 0, consecutiveFailures: 0, lastError: null,
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
    runStatus: 'idle', failureCount: 2, consecutiveFailures: 1, lastError: 'Failed stocks: NVDA',
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
    runStatus: 'running', failureCount: 0, consecutiveFailures: 0, lastError: null,
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
    runStatus: 'idle', failureCount: 5, consecutiveFailures: 3, lastError: 'LLM connection timeout',
    createdAt: '2026-03-20T09:00:00',
  },
];

// ============ History & Report Mock Data ============

export const MOCK_HISTORY_ITEMS: HistoryItem[] = [
  // 600519 贵州茅台 × 3
  { id: 1, queryId: 'q-001', stockCode: '600519', stockName: '贵州茅台', reportType: 'detailed', sentimentScore: 72, operationAdvice: '持有观望，等待回调加仓', createdAt: '2026-04-08T15:30:00' },
  { id: 2, queryId: 'q-002', stockCode: '600519', stockName: '贵州茅台', reportType: 'detailed', sentimentScore: 68, operationAdvice: '量能萎缩，短线谨慎', createdAt: '2026-04-07T15:30:00' },
  { id: 3, queryId: 'q-003', stockCode: '600519', stockName: '贵州茅台', reportType: 'detailed', sentimentScore: 65, operationAdvice: '均线支撑有效，可继续持有', createdAt: '2026-04-06T15:30:00' },
  // 300750 宁德时代 × 3
  { id: 4, queryId: 'q-004', stockCode: '300750', stockName: '宁德时代', reportType: 'detailed', sentimentScore: 78, operationAdvice: '放量突破，可加仓', createdAt: '2026-04-08T15:30:00' },
  { id: 5, queryId: 'q-005', stockCode: '300750', stockName: '宁德时代', reportType: 'detailed', sentimentScore: 70, operationAdvice: '震荡蓄势，等待方向', createdAt: '2026-04-07T15:30:00' },
  { id: 6, queryId: 'q-006', stockCode: '300750', stockName: '宁德时代', reportType: 'detailed', sentimentScore: 62, operationAdvice: '缩量回调，关注支撑位', createdAt: '2026-04-06T15:30:00' },
  // 002594 比亚迪 × 3
  { id: 7, queryId: 'q-007', stockCode: '002594', stockName: '比亚迪', reportType: 'detailed', sentimentScore: 75, operationAdvice: '趋势向好，可适量加仓', createdAt: '2026-04-08T15:30:00' },
  { id: 8, queryId: 'q-008', stockCode: '002594', stockName: '比亚迪', reportType: 'detailed', sentimentScore: 71, operationAdvice: '板块轮动受益，持有', createdAt: '2026-04-07T15:30:00' },
  { id: 9, queryId: 'q-009', stockCode: '002594', stockName: '比亚迪', reportType: 'detailed', sentimentScore: 66, operationAdvice: '技术面中性，观望为主', createdAt: '2026-04-06T15:30:00' },
  // 000858 五粮液 × 3
  { id: 10, queryId: 'q-010', stockCode: '000858', stockName: '五粮液', reportType: 'detailed', sentimentScore: 55, operationAdvice: '中性偏弱，建议观望', createdAt: '2026-04-08T15:30:00' },
  { id: 11, queryId: 'q-011', stockCode: '000858', stockName: '五粮液', reportType: 'detailed', sentimentScore: 52, operationAdvice: '弱势震荡，不宜追高', createdAt: '2026-04-07T15:30:00' },
  { id: 12, queryId: 'q-012', stockCode: '000858', stockName: '五粮液', reportType: 'detailed', sentimentScore: 48, operationAdvice: '跌破均线支撑，减仓', createdAt: '2026-04-06T15:30:00' },
  // 601318 中国平安 × 3
  { id: 13, queryId: 'q-013', stockCode: '601318', stockName: '中国平安', reportType: 'detailed', sentimentScore: 63, operationAdvice: '估值偏低，长线可配置', createdAt: '2026-04-08T15:30:00' },
  { id: 14, queryId: 'q-014', stockCode: '601318', stockName: '中国平安', reportType: 'detailed', sentimentScore: 60, operationAdvice: '保险板块回暖，关注', createdAt: '2026-04-07T15:30:00' },
  { id: 15, queryId: 'q-015', stockCode: '601318', stockName: '中国平安', reportType: 'detailed', sentimentScore: 58, operationAdvice: '底部震荡，耐心等待', createdAt: '2026-04-06T15:30:00' },
];

export const MOCK_HISTORY_GROUPS: HistoryGroupItem[] = [
  { stockCode: '600519', stockName: '贵州茅台', recordCount: 3, latestId: 1, latestSentimentScore: 72, latestOperationAdvice: '持有观望，等待回调加仓', latestCreatedAt: '2026-04-08T15:30:00' },
  { stockCode: '300750', stockName: '宁德时代', recordCount: 3, latestId: 4, latestSentimentScore: 78, latestOperationAdvice: '放量突破，可加仓', latestCreatedAt: '2026-04-08T15:30:00' },
  { stockCode: '002594', stockName: '比亚迪', recordCount: 3, latestId: 7, latestSentimentScore: 75, latestOperationAdvice: '趋势向好，可适量加仓', latestCreatedAt: '2026-04-08T15:30:00' },
  { stockCode: '000858', stockName: '五粮液', recordCount: 3, latestId: 10, latestSentimentScore: 55, latestOperationAdvice: '中性偏弱，建议观望', latestCreatedAt: '2026-04-08T15:30:00' },
  { stockCode: '601318', stockName: '中国平安', recordCount: 3, latestId: 13, latestSentimentScore: 63, latestOperationAdvice: '估值偏低，长线可配置', latestCreatedAt: '2026-04-08T15:30:00' },
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

// ============ Report: 宁德时代 ============

export const MOCK_REPORT_NINGDE: AnalysisReport = {
  meta: {
    id: 4, queryId: 'q-004', stockCode: '300750', stockName: '宁德时代',
    reportType: 'detailed', reportLanguage: 'zh',
    createdAt: '2026-04-08T15:30:00', currentPrice: 218.50, changePct: 3.42,
    modelUsed: 'grok-4-1-fast',
  },
  summary: {
    analysisSummary: `## 宁德时代（300750）技术分析报告

### 一句话结论
**看多** — 建议仓位 70%

宁德时代放量突破前期平台，MACD 金叉确认，量价齐升态势明显。新能源板块政策利好持续释放，固态电池技术突破预期强化。

### 技术面分析

**趋势判断：上升趋势加速**
- MA5(215) > MA10(210) > MA20(205) > MA60(195)，均线多头排列
- MACD(1.85) 零轴上方金叉，红柱快速放大
- 布林带开口扩大，价格突破上轨

**动量指标**
- RSI(14) = 76.8，强势区间
- KDJ：K=82.5, D=75.3, J=96.9，超买区但趋势强劲
- CCI(14) = 158，极强

**量价关系**
- 近5日成交量均值较20日均量放大 62%
- OBV 创近期新高，主力资金持续流入
- 换手率 3.25%，交投活跃

### 筹码分析
- 获利盘比例：78.5%
- 成本集中度(90%)：195-225
- 上方套牢盘较少，突破阻力小

### 基本面速览
- PE(TTM): 22.8 | PB: 5.2
- 净利润增速(YoY): 28.6%
- 机构持仓占比: 68.5%
- 北向资金近5日净买入: +15.8亿`,
    operationAdvice: '放量突破，可加仓',
    trendPrediction: '短期看涨，目标位 230-240',
    sentimentScore: 78,
    sentimentLabel: '乐观',
  },
  strategy: {
    idealBuy: '210-215（回踩MA5）',
    secondaryBuy: '200-205（MA20支撑）',
    stopLoss: '192（跌破MA60）',
    takeProfit: '240（前高压力位）',
  },
  details: {
    newsContent: `**近期重要新闻：**
1. 宁德时代发布全固态电池样品，能量密度突破500Wh/kg
2. 与多家欧洲车企签署长期供货协议，海外订单大幅增长
3. 麒麟电池产能持续爬坡，装车量环比增长45%
4. 新能源汽车补贴政策延续，行业景气度维持高位`,
    belongBoards: [
      { name: '锂电池', code: 'BK0573', type: 'industry' },
      { name: '新能源', code: 'BK0478', type: 'concept' },
      { name: '创业板综', code: 'BK0638', type: 'concept' },
    ],
    sectorRankings: {
      top: [
        { name: '锂电池', changePct: 3.65 },
        { name: '新能源车', changePct: 2.88 },
        { name: '储能', changePct: 2.15 },
      ],
      bottom: [
        { name: '白酒', changePct: -0.85 },
        { name: '房地产', changePct: -1.52 },
      ],
    },
  },
};

// ============ Report: 比亚迪 ============

export const MOCK_REPORT_BYD: AnalysisReport = {
  meta: {
    id: 7, queryId: 'q-007', stockCode: '002594', stockName: '比亚迪',
    reportType: 'detailed', reportLanguage: 'zh',
    createdAt: '2026-04-08T15:30:00', currentPrice: 312.80, changePct: 2.15,
    modelUsed: 'grok-4-1-fast',
  },
  summary: {
    analysisSummary: `## 比亚迪（002594）技术分析报告

### 一句话结论
**看多** — 建议仓位 65%

比亚迪近期受新能源汽车销量数据超预期提振，股价沿5日均线稳步上行。技术面均线多头排列，MACD持续放量，但RSI接近超买需注意短期回调风险。

### 技术面分析

**趋势判断：上升趋势**
- MA5(310) > MA10(305) > MA20(298) > MA60(280)，均线多头排列
- MACD(1.52) 零轴上方运行，红柱温和放大
- 布林带中轨上行，价格在中上轨间运行

**动量指标**
- RSI(14) = 71.2，强势区间
- KDJ：K=75.8, D=70.2, J=87.0，偏强运行
- CCI(14) = 112，强势

**量价关系**
- 近5日成交量均值较20日均量放大 28%
- OBV 稳步上升，资金持续流入
- 换手率 1.85%，活跃度良好

### 筹码分析
- 获利盘比例：82.3%
- 成本集中度(90%)：275-320
- 套牢盘主要分布在 330-350 区间

### 基本面速览
- PE(TTM): 25.6 | PB: 6.8
- 净利润增速(YoY): 32.5%
- 机构持仓占比: 72.1%
- 北向资金近5日净买入: +12.5亿`,
    operationAdvice: '趋势向好，可适量加仓',
    trendPrediction: '短期看涨，目标位 325-335',
    sentimentScore: 75,
    sentimentLabel: '乐观',
  },
  strategy: {
    idealBuy: '305-308（回踩MA10）',
    secondaryBuy: '295-298（MA20支撑）',
    stopLoss: '278（跌破MA60）',
    takeProfit: '335（前高压力位）',
  },
  details: {
    newsContent: `**近期重要新闻：**
1. 比亚迪3月销量突破38万辆，同比增长45%，再创历史新高
2. 第五代DM技术发布，百公里油耗降至2.9L
3. 海外市场持续扩张，巴西工厂正式投产
4. 智能驾驶"天神之眼"系统获多项技术突破`,
    belongBoards: [
      { name: '新能源车', code: 'BK0477', type: 'industry' },
      { name: '深股通', code: 'BK0804', type: 'concept' },
      { name: '智能驾驶', code: 'BK0892', type: 'concept' },
    ],
    sectorRankings: {
      top: [
        { name: '新能源车', changePct: 2.88 },
        { name: '锂电池', changePct: 3.65 },
        { name: '智能驾驶', changePct: 1.92 },
      ],
      bottom: [
        { name: '房地产', changePct: -1.52 },
        { name: '银行', changePct: -0.65 },
      ],
    },
  },
};

// ============ Report: 五粮液 ============

export const MOCK_REPORT_WULIANGYE: AnalysisReport = {
  meta: {
    id: 10, queryId: 'q-010', stockCode: '000858', stockName: '五粮液',
    reportType: 'detailed', reportLanguage: 'zh',
    createdAt: '2026-04-08T15:30:00', currentPrice: 142.30, changePct: -0.85,
    modelUsed: 'grok-4-1-fast',
  },
  summary: {
    analysisSummary: `## 五粮液（000858）技术分析报告

### 一句话结论
**中性** — 建议仓位 30%

五粮液近期走势偏弱，均线系统趋于粘合，MACD在零轴附近震荡。白酒板块整体承压，市场对消费复苏预期分歧较大，短期缺乏明确方向。

### 技术面分析

**趋势判断：震荡整理**
- MA5(143) ≈ MA10(143.5) ≈ MA20(144)，均线粘合
- MACD(-0.12) 零轴附近震荡，绿柱缩短
- 布林带收窄，价格在中轨附近运行

**动量指标**
- RSI(14) = 45.8，中性区间
- KDJ：K=42.5, D=45.8, J=35.9，偏弱
- CCI(14) = -18，中性偏弱

**量价关系**
- 近5日成交量均值较20日均量萎缩 15%
- OBV 走平，资金观望情绪浓厚
- 换手率 0.52%，交投清淡

### 筹码分析
- 获利盘比例：52.8%
- 成本集中度(90%)：135-155
- 上下套牢盘分布较均匀

### 基本面速览
- PE(TTM): 18.5 | PB: 4.2
- 净利润增速(YoY): 8.5%
- 机构持仓占比: 75.2%
- 北向资金近5日净买入: -2.1亿`,
    operationAdvice: '中性偏弱，建议观望',
    trendPrediction: '短期震荡，区间 138-148',
    sentimentScore: 55,
    sentimentLabel: '中性',
  },
  strategy: {
    idealBuy: '138-140（布林下轨支撑）',
    secondaryBuy: '132-135（前低支撑）',
    stopLoss: '128（跌破前低）',
    takeProfit: '152（布林上轨压力）',
  },
  details: {
    newsContent: `**近期重要新闻：**
1. 五粮液2025年年报：营收同比增长10.5%，净利润同比增长8.5%，略低于预期
2. 普五批价稳定在960-980元，渠道库存处于中等水平
3. 白酒行业进入调整期，高端白酒竞争加剧
4. 公司推出年轻化产品线，布局中低端市场`,
    belongBoards: [
      { name: '白酒', code: 'BK0477', type: 'industry' },
      { name: '四川板块', code: 'BK0158', type: 'region' },
      { name: '深股通', code: 'BK0804', type: 'concept' },
    ],
    sectorRankings: {
      top: [
        { name: '新能源车', changePct: 2.88 },
        { name: '锂电池', changePct: 3.65 },
        { name: '半导体', changePct: 1.55 },
      ],
      bottom: [
        { name: '白酒', changePct: -0.85 },
        { name: '房地产', changePct: -1.52 },
      ],
    },
  },
};

// ============ Report: 中国平安 ============

export const MOCK_REPORT_PINGAN: AnalysisReport = {
  meta: {
    id: 13, queryId: 'q-013', stockCode: '601318', stockName: '中国平安',
    reportType: 'detailed', reportLanguage: 'zh',
    createdAt: '2026-04-08T15:30:00', currentPrice: 52.80, changePct: 0.95,
    modelUsed: 'grok-4-1-fast',
  },
  summary: {
    analysisSummary: `## 中国平安（601318）技术分析报告

### 一句话结论
**中性偏多** — 建议仓位 45%

中国平安近期底部企稳迹象明显，MACD底背离后金叉，成交量温和放大。保险板块受益于利率预期变化，估值处于历史低位具备修复空间。

### 技术面分析

**趋势判断：底部企稳**
- MA5(52.5) > MA10(52.0)，短期均线金叉
- MA20(51.8) 走平，MA60(50.5) 开始拐头
- MACD(0.15) 零轴附近金叉，红柱初现

**动量指标**
- RSI(14) = 55.2，中性偏强
- KDJ：K=58.5, D=52.8, J=69.9，温和向上
- CCI(14) = 45，中性

**量价关系**
- 近5日成交量均值较20日均量放大 18%
- OBV 底部抬升，资金开始回流
- 换手率 0.65%，活跃度回升

### 筹码分析
- 获利盘比例：45.2%
- 成本集中度(90%)：48-56
- 下方密集成交区 49-51 形成支撑

### 基本面速览
- PE(TTM): 8.5 | PB: 0.95
- 净利润增速(YoY): 12.8%
- 机构持仓占比: 65.8%
- 北向资金近5日净买入: +5.2亿`,
    operationAdvice: '估值偏低，长线可配置',
    trendPrediction: '短期震荡偏强，目标位 55-58',
    sentimentScore: 63,
    sentimentLabel: '乐观',
  },
  strategy: {
    idealBuy: '51-52（MA20附近）',
    secondaryBuy: '49-50（MA60支撑）',
    stopLoss: '47（跌破前低）',
    takeProfit: '58（前高压力位）',
  },
  details: {
    newsContent: `**近期重要新闻：**
1. 中国平安2025年年报：归母净利润同比增长12.8%，寿险新业务价值增长22%
2. 平安银行零售转型成效显著，不良率持续下降
3. 保险行业报行合一政策落地，龙头公司受益
4. 平安医疗健康生态圈用户突破5亿`,
    belongBoards: [
      { name: '保险', code: 'BK0474', type: 'industry' },
      { name: '沪股通', code: 'BK0707', type: 'concept' },
      { name: '金融科技', code: 'BK0800', type: 'concept' },
    ],
    sectorRankings: {
      top: [
        { name: '保险', changePct: 1.85 },
        { name: '银行', changePct: 0.92 },
        { name: '券商', changePct: 0.75 },
      ],
      bottom: [
        { name: '光伏', changePct: -2.15 },
        { name: '白酒', changePct: -0.85 },
      ],
    },
  },
};

/** Map stock code → mock report */
export const MOCK_REPORTS_MAP: Record<string, AnalysisReport> = {
  '600519': MOCK_REPORT_MAOTAI,
  '300750': MOCK_REPORT_NINGDE,
  '002594': MOCK_REPORT_BYD,
  '000858': MOCK_REPORT_WULIANGYE,
  '601318': MOCK_REPORT_PINGAN,
};

// ============ Chat Mock Data ============

export const MOCK_CHAT_SKILLS: SkillInfo[] = [
  { id: 'bull_trend', name: '趋势分析', description: '基于均线、MACD、布林带等指标进行趋势判断' },
  { id: 'chan_theory', name: '缠论分析', description: '运用缠中说禅理论进行走势分析和买卖点判断' },
  { id: 'chip_analysis', name: '筹码分析', description: '分析筹码分布、获利盘比例和主力成本' },
  { id: 'comprehensive', name: '综合分析', description: '技术面+基本面+消息面综合研判' },
];

export const MOCK_CHAT_SESSIONS: ChatSessionItem[] = [
  { session_id: 'demo-s1', title: '贵州茅台趋势分析', message_count: 4, created_at: '2026-04-08T10:00:00', last_active: '2026-04-08T10:15:00' },
  { session_id: 'demo-s2', title: '宁德时代缠论分析', message_count: 6, created_at: '2026-04-07T14:00:00', last_active: '2026-04-07T14:30:00' },
  { session_id: 'demo-s3', title: '比亚迪综合研判', message_count: 3, created_at: '2026-04-06T09:00:00', last_active: '2026-04-06T09:20:00' },
];

// ============ Settings Mock Data ============

export const MOCK_SYSTEM_CONFIG_ITEMS: SystemConfigItem[] = [
  // base
  { key: 'REPORT_LANGUAGE', value: 'zh', rawValueExists: true, isMasked: false, schema: { key: 'REPORT_LANGUAGE', title: '报告语言', description: '分析报告的输出语言', category: 'base', dataType: 'string', uiControl: 'select', isSensitive: false, isRequired: false, isEditable: true, options: [{ label: '中文', value: 'zh' }, { label: 'English', value: 'en' }], validation: {}, displayOrder: 10 } },
  { key: 'DEFAULT_REPORT_TYPE', value: 'detailed', rawValueExists: true, isMasked: false, schema: { key: 'DEFAULT_REPORT_TYPE', title: '默认报告类型', description: '默认的分析报告详细程度', category: 'base', dataType: 'string', uiControl: 'select', isSensitive: false, isRequired: false, isEditable: true, options: [{ label: '简要', value: 'simple' }, { label: '详细', value: 'detailed' }, { label: '完整', value: 'full' }], validation: {}, displayOrder: 20 } },
  // ai_model
  { key: 'LLM_PROVIDER', value: 'openai', rawValueExists: true, isMasked: false, schema: { key: 'LLM_PROVIDER', title: 'LLM 提供商', description: '大语言模型服务提供商', category: 'ai_model', dataType: 'string', uiControl: 'select', isSensitive: false, isRequired: true, isEditable: true, options: ['openai', 'anthropic', 'google', 'deepseek'], validation: {}, displayOrder: 10 } },
  { key: 'LLM_MODEL', value: 'grok-4-1-fast', rawValueExists: true, isMasked: false, schema: { key: 'LLM_MODEL', title: '模型名称', description: '使用的具体模型', category: 'ai_model', dataType: 'string', uiControl: 'text', isSensitive: false, isRequired: true, isEditable: true, options: [], validation: {}, displayOrder: 20 } },
  { key: 'LLM_API_KEY', value: '******', rawValueExists: true, isMasked: true, schema: { key: 'LLM_API_KEY', title: 'API Key', description: 'LLM 服务的 API 密钥', category: 'ai_model', dataType: 'string', uiControl: 'password', isSensitive: true, isRequired: true, isEditable: true, options: [], validation: {}, displayOrder: 30 } },
  { key: 'LLM_BASE_URL', value: 'https://api.x.ai/v1', rawValueExists: true, isMasked: false, schema: { key: 'LLM_BASE_URL', title: 'API 地址', description: 'LLM 服务的 API 基础地址', category: 'ai_model', dataType: 'string', uiControl: 'text', isSensitive: false, isRequired: false, isEditable: true, options: [], validation: {}, displayOrder: 40 } },
  // data_source
  { key: 'DATA_PROVIDER_PRIORITY', value: 'efinance,akshare,pytdx', rawValueExists: true, isMasked: false, schema: { key: 'DATA_PROVIDER_PRIORITY', title: '数据源优先级', description: '行情数据源的使用优先级', category: 'data_source', dataType: 'string', uiControl: 'text', isSensitive: false, isRequired: false, isEditable: true, options: [], validation: { multiValue: true }, displayOrder: 10 } },
  { key: 'REALTIME_PROVIDER_PRIORITY', value: 'tencent,akshare_sina,efinance', rawValueExists: true, isMasked: false, schema: { key: 'REALTIME_PROVIDER_PRIORITY', title: '实时行情优先级', description: '实时行情数据源的使用优先级', category: 'data_source', dataType: 'string', uiControl: 'text', isSensitive: false, isRequired: false, isEditable: true, options: [], validation: { multiValue: true }, displayOrder: 20 } },
  // notification
  { key: 'BARK_ENABLED', value: 'false', rawValueExists: true, isMasked: false, schema: { key: 'BARK_ENABLED', title: 'Bark 推送', description: '启用 Bark 推送通知', category: 'notification', dataType: 'boolean', uiControl: 'switch', isSensitive: false, isRequired: false, isEditable: true, options: [], validation: {}, displayOrder: 10 } },
  { key: 'BARK_URL', value: '', rawValueExists: false, isMasked: false, schema: { key: 'BARK_URL', title: 'Bark 地址', description: 'Bark 推送服务地址', category: 'notification', dataType: 'string', uiControl: 'text', isSensitive: false, isRequired: false, isEditable: true, options: [], validation: {}, displayOrder: 20 } },
  // system
  { key: 'LOG_LEVEL', value: 'INFO', rawValueExists: true, isMasked: false, schema: { key: 'LOG_LEVEL', title: '日志级别', description: '系统日志输出级别', category: 'system', dataType: 'string', uiControl: 'select', isSensitive: false, isRequired: false, isEditable: true, options: ['DEBUG', 'INFO', 'WARNING', 'ERROR'], validation: {}, displayOrder: 10 } },
  { key: 'SCHEDULER_ENABLED', value: 'true', rawValueExists: true, isMasked: false, schema: { key: 'SCHEDULER_ENABLED', title: '定时任务', description: '启用定时分析任务调度', category: 'system', dataType: 'boolean', uiControl: 'switch', isSensitive: false, isRequired: false, isEditable: true, options: [], validation: {}, displayOrder: 20 } },
];

/** Set to true to use mock data instead of API calls */
export const USE_MOCK = false;

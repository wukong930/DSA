# -*- coding: utf-8 -*-
"""Text report generator for backtest results.

Generates human-readable Chinese reports from BacktestReport.
Uses enriched trade data (from TradeEnricher) when available.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from src.backtest_bt.metrics import BacktestReport


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    show_trade_details: bool = True
    max_trade_details: int = 20       # Max trades to show in detail section
    show_monthly: bool = True
    show_rebalance: bool = True
    precision: int = 2                # Decimal places for percentages


def generate_text_report(report: BacktestReport, config: Optional[ReportConfig] = None) -> str:
    """Generate a full text report from a BacktestReport.

    Args:
        report: The computed backtest report.
        config: Optional report configuration.

    Returns:
        Formatted multi-section text report.
    """
    if config is None:
        config = ReportConfig()

    sections = []

    # ---- Header ----
    sections.append(_section_header(report))

    # ---- Summary ----
    sections.append(_section_summary(report, config))

    # ---- Trade Details ----
    if config.show_trade_details and report.trade_list:
        sections.append(_section_trades(report, config))

    # ---- Risk Analysis ----
    sections.append(_section_risk(report, config))

    # ---- Monthly Returns ----
    if config.show_monthly and report.monthly_returns:
        sections.append(_section_monthly(report))

    # ---- Rebalance History ----
    if config.show_rebalance and report.rebalance_history:
        sections.append(_section_rebalance(report))

    # ---- Warnings ----
    if report.warnings:
        sections.append(_section_warnings(report))

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Section generators
# ---------------------------------------------------------------------------

def _section_header(report: BacktestReport) -> str:
    """Report header with period and strategy info."""
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "  策 略 回 测 报 告",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    # Extract period from equity curve if available
    if report.equity_curve:
        first_date = report.equity_curve[0].get("date", "")
        last_date = report.equity_curve[-1].get("date", "")
        if first_date and last_date:
            lines.append(f"  回测区间：{first_date} ~ {last_date}")
    if hasattr(report, "strategy_name") and report.strategy_name:
        lines.append(f"  策略名称：{report.strategy_name}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def _section_summary(report: BacktestReport, cfg: ReportConfig) -> str:
    """Executive summary section."""
    p = cfg.precision
    lines = [
        "一、执行摘要",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    def f(v: float) -> str:
        return f"{v:+.{p}f}%"

    def n(v, suffix="") -> str:
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            return "—"
        if isinstance(v, float):
            return f"{v:.{p}f}{suffix}"
        return str(v)

    # Performance
    lines.append("  【收益概况】")
    lines.append(f"  总收益率：  {f(report.total_return_pct)}")
    lines.append(f"  年化收益率：{f(report.annual_return_pct)}")
    if report.alpha is not None:
        lines.append(f"  Alpha：     {f(report.alpha)}")
    if report.beta is not None:
        lines.append(f"  Beta：      {n(report.beta)}")
    lines.append(f"  夏普比率：  {n(report.sharpe_ratio)}")
    lines.append(f"  索提诺比率：{n(report.sortino_ratio)}")
    lines.append(f"  卡玛比率：  {n(report.calmar_ratio)}")

    # Risk
    lines.append("  【风险指标】")
    lines.append(f"  最大回撤：  {f(-abs(report.max_drawdown_pct))}")
    lines.append(f"  回撤持续：  {report.max_drawdown_duration_days} 个交易日")
    lines.append(f"  年化波动率：{f(report.volatility_annual)}")
    lines.append(f"  VaR(95%)： {f(-abs(report.var_95))}")
    lines.append(f"  CVaR(95%)：{f(-abs(report.cvar_95))}")

    # Trades
    lines.append("  【交易统计】")
    lines.append(f"  总交易次数：{report.total_trades}")
    lines.append(f"  胜率：      {n(report.win_rate_pct)}%")
    lines.append(f"  盈亏比：    {n(report.profit_loss_ratio)}")
    lines.append(f"  平均持仓：  {n(report.avg_holding_days)} 天")
    lines.append(f"  单笔盈亏：  {n(report.avg_profit_per_trade)}%")
    lines.append(f"  最大连胜：  {report.max_consecutive_wins} 次")
    lines.append(f"  最大连亏：  {report.max_consecutive_losses} 次")

    return "\n".join(lines)


def _section_trades(report: BacktestReport, cfg: ReportConfig) -> str:
    """Trade detail section — shows enriched trade records."""
    trades = report.trade_list
    max_show = min(cfg.max_trade_details, len(trades))
    display_trades = trades[:max_show]

    lines = [
        "二、买卖点详情",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Check if trades are enriched (have entry_price field)
    enriched = any(t.get("entry_price") is not None for t in display_trades)

    if enriched:
        # Enriched format — show prices and signals
        lines.append(
            f"  {'代码':<10} {'买入日期':<12} {'买价':>8} {'卖出日期':<12} "
            f"{'卖价':>8} {'收益率':>8} {'持仓(天)':>8}"
        )
        lines.append("  " + "─" * 80)

        for t in display_trades:
            code = t.get("code", "?")[:10]
            entry_d = t.get("entry_date", "?")[:10]
            exit_d = t.get("exit_date", "?")[:10]
            entry_p = t.get("entry_price")
            exit_p = t.get("exit_price")
            ret = t.get("return_pct", 0)
            days = t.get("holding_days", 0)
            signal = t.get("entry_signal", "")
            exit_r = t.get("exit_reason", "")

            entry_s = f"{entry_p:.2f}" if entry_p else "—"
            exit_s = f"{exit_p:.2f}" if exit_p else "—"
            ret_s = f"{ret:+.2f}%"
            days_s = f"{days}"

            lines.append(
                f"  {code:<10} {entry_d:<12} {entry_s:>8} {exit_d:<12} "
                f"{exit_s:>8} {ret_s:>8} {days_s:>8}"
            )
            # Show signal and exit reason on next line
            if signal and signal != "未记录":
                lines.append(f"  ├─ 入场信号：{signal}")
            if exit_r and exit_r != "未记录":
                lines.append(f"  └─ 退出原因：{exit_r}")
            if signal != "未记录" or exit_r != "未记录":
                lines.append("")
    else:
        # Basic format — show only available fields
        lines.append(
            f"  {'代码':<10} {'买入日期':<12} {'卖出日期':<12} "
            f"{'收益率':>8} {'持仓(天)':>8} {'盈亏':>12}"
        )
        lines.append("  " + "─" * 66)
        for t in display_trades:
            code = t.get("code", "?")[:10]
            entry_d = t.get("entry_date", "?")[:10]
            exit_d = t.get("exit_date", "?")[:10]
            ret = t.get("return_pct", 0)
            days = t.get("holding_days", 0)
            pnl = t.get("pnl", 0)
            ret_s = f"{ret:+.2f}%"
            pnl_s = f"{pnl:+,.2f}"
            lines.append(
                f"  {code:<10} {entry_d:<12} {exit_d:<12} "
                f"{ret_s:>8} {days:>8} {pnl_s:>12}"
            )

    if max_show < len(trades):
        lines.append(f"\n  ... 共 {len(trades)} 笔交易，以上显示前 {max_show} 笔")

    return "\n".join(lines)


def _section_risk(report: BacktestReport, cfg: ReportConfig) -> str:
    """Risk analysis section."""
    p = cfg.precision
    lines = [
        "三、风险分析",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    def f(v: float) -> str:
        return f"{v:+.{p}f}%"

    def n(v, suffix="") -> str:
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            return "—"
        if isinstance(v, float):
            return f"{v:.{p}f}{suffix}"
        return str(v)

    # Find max drawdown period
    max_dd = abs(report.max_drawdown_pct)
    dd_duration = report.max_drawdown_duration_days
    lines.append(f"  最大单次回撤：  {f(-max_dd)}  （持续 {dd_duration} 个交易日）")

    if report.information_ratio is not None:
        lines.append(f"  信息比率：      {n(report.information_ratio)}")
    if report.alpha is not None:
        lines.append(f"  Alpha（年化）： {f(report.alpha)}")
    if report.beta is not None:
        lines.append(f"  Beta：          {n(report.beta)}")

    lines.append(f"  日波动率：      {n(report.volatility_annual / math.sqrt(244))}%")
    lines.append(f"  VaR (95%)：    {f(-abs(report.var_95))} / 日")
    lines.append(f"  CVaR (95%)：   {f(-abs(report.cvar_95))} / 日")

    # Win/loss breakdown
    wins = [t for t in report.trade_list if t.get("return_pct", 0) > 0]
    losses = [t for t in report.trade_list if t.get("return_pct", 0) < 0]
    if wins or losses:
        avg_win = sum(t.get("return_pct", 0) for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.get("return_pct", 0) for t in losses) / len(losses) if losses else 0
        lines.append(f"  平均单笔盈利：  {f(avg_win)}  （{len(wins)} 笔）")
        lines.append(f"  平均单笔亏损：  {f(avg_loss)}  （{len(losses)} 笔）")
        lines.append(f"  盈亏比：        {n(report.profit_loss_ratio)}")

    return "\n".join(lines)


def _section_monthly(report: BacktestReport) -> str:
    """Monthly returns table."""
    rows = report.monthly_returns
    if not rows:
        return ""

    lines = [
        "四、月度收益",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    # Header
    lines.append(f"  {'年份':<6} {'月份':<6} {'收益率':>10} {'风格':<10}")
    lines.append("  " + "─" * 40)

    for r in rows:
        year = r.get("year", "?")
        month = r.get("month", "?")
        ret = r.get("return_pct", 0)
        # Visual bar
        bar_len = int(min(abs(ret) / 5, 10))
        bar = "█" * bar_len if ret >= 0 else "▓" * bar_len
        sign = "+" if ret >= 0 else ""
        style = "盈利" if ret >= 0 else "亏损"
        lines.append(f"  {year:<6} {month:<6} {sign}{ret:>8.2f}%  {style}")

    # Monthly return statistics
    all_returns = [r.get("return_pct", 0) for r in rows]
    if all_returns:
        positive = [r for r in all_returns if r > 0]
        lines.append(
            f"  月均收益：{sum(all_returns) / len(all_returns):+.2f}%"
            f"  盈利月数：{len(positive)}/{len(all_returns)}"
        )

    return "\n".join(lines)


def _section_rebalance(report: BacktestReport) -> str:
    """Rebalance history section."""
    history = report.rebalance_history
    if not history:
        return ""

    lines = [
        "五、再平衡记录",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"  共 {len(history)} 次再平衡",
        "",
    ]

    for entry in history:
        win = entry.get("window", "?")
        start = entry.get("start", "?")
        end = entry.get("end", "?")
        codes = entry.get("codes", [])
        total = entry.get("total_codes", 0)
        codes_str = ", ".join(str(c) for c in codes[:5])
        if total > len(codes):
            codes_str += f" ... (+{total - len(codes)} 只)"
        lines.append(
            f"  第 {win} 期：{start} ~ {end}"
        )
        lines.append(f"  └─ 选股 {total} 只：{codes_str}")

    return "\n".join(lines)


def _section_warnings(report: BacktestReport) -> str:
    """Warnings section."""
    lines = [
        "六、警告与说明",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]
    if report.benchmark_warning:
        lines.append(f"  ⚠ {report.benchmark_warning}")
    for w in report.warnings:
        lines.append(f"  ⚠ {w}")
    if report.skipped_codes:
        lines.append(f"  ⚠ 跳过无数据股票 {len(report.skipped_codes)} 只：{report.skipped_codes[:10]}")
        if len(report.skipped_codes) > 10:
            lines[-1] += f" ... (+{len(report.skipped_codes) - 10} 只)"
    return "\n".join(lines)


def generate_trade_summary(trades: list[dict]) -> str:
    """Generate a compact single-line summary of trades for quick review."""
    if not trades:
        return "无交易记录"

    wins = [t for t in trades if t.get("return_pct", 0) > 0]
    losses = [t for t in trades if t.get("return_pct", 0) < 0]
    total_ret = sum(t.get("return_pct", 0) for t in trades)
    avg_days = sum(t.get("holding_days", 0) for t in trades) / len(trades) if trades else 0

    parts = [
        f"共 {len(trades)} 笔",
        f"胜率 {len(wins) / len(trades) * 100:.0f}%" if trades else "胜率 —",
        f"总收益 {total_ret:+.1f}%",
        f"均持仓 {avg_days:.0f} 天",
    ]
    return "  |  ".join(parts)

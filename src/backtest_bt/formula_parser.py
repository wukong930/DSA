# -*- coding: utf-8 -*-
"""策略表达式拆分器：将完整策略公式自动拆分为买入/卖出条件。"""

from __future__ import annotations

import re
import logging

from src.backtest_bt.formula_translator import translate_formula, is_tdx_formula

logger = logging.getLogger(__name__)

# 卖出关键词模式
_SELL_PATTERNS = re.compile(
    r'卖出|sell|平仓|清仓|死叉|death.?cross',
    re.IGNORECASE,
)

# 买入关键词模式
_BUY_PATTERNS = re.compile(
    r'买入|buy|开仓|建仓|金叉|golden.?cross',
    re.IGNORECASE,
)


def parse_strategy_expression(raw: str) -> dict:
    """将完整策略表达式拆分为买入/卖出条件。

    支持的格式：
    1. 分号或换行分隔的两条表达式（自动识别买/卖）
    2. 含中文标注的表达式（如 "买入: xxx; 卖出: yyy"）
    3. 单条表达式（买入=表达式，卖出=取反）

    Returns:
        {"buy_expression": str, "sell_expression": str, "translated": str | None}
    """
    raw = raw.strip()
    if not raw:
        return {"buy_expression": "", "sell_expression": "", "translated": None}

    # Split by ; or newline
    parts = re.split(r'[;\n]+', raw)
    parts = [p.strip() for p in parts if p.strip()]

    buy_expr = ""
    sell_expr = ""
    translated = None

    if len(parts) >= 2:
        # Try to identify which is buy and which is sell
        buy_candidates = []
        sell_candidates = []

        for part in parts:
            # Strip label prefixes like "买入:" or "sell:"
            cleaned = re.sub(
                r'^(买入|卖出|buy|sell|开仓|平仓|建仓|清仓)\s*[:：]\s*',
                '', part, flags=re.IGNORECASE,
            )

            if _SELL_PATTERNS.search(part) and not _BUY_PATTERNS.search(part):
                sell_candidates.append(cleaned)
            elif _BUY_PATTERNS.search(part) and not _SELL_PATTERNS.search(part):
                buy_candidates.append(cleaned)
            elif not buy_candidates:
                buy_candidates.append(cleaned)
            else:
                sell_candidates.append(cleaned)

        buy_expr = ' & '.join(f'({c})' for c in buy_candidates) if buy_candidates else parts[0]
        sell_expr = ' & '.join(f'({c})' for c in sell_candidates) if sell_candidates else parts[-1]

        # If still same, first=buy, last=sell
        if buy_expr == sell_expr and len(parts) >= 2:
            buy_expr = parts[0]
            sell_expr = parts[-1]
            # Strip labels again
            buy_expr = re.sub(r'^(买入|buy|开仓|建仓|金叉)\s*[:：]\s*', '', buy_expr, flags=re.IGNORECASE)
            sell_expr = re.sub(r'^(卖出|sell|平仓|清仓|死叉)\s*[:：]\s*', '', sell_expr, flags=re.IGNORECASE)
    else:
        # Single expression: buy=expr, sell=negation
        buy_expr = parts[0]
        buy_expr = re.sub(r'^(买入|buy|开仓|建仓)\s*[:：]\s*', '', buy_expr, flags=re.IGNORECASE)
        sell_expr = f'~({buy_expr})'

    # Translate if TDX syntax
    if is_tdx_formula(buy_expr) or is_tdx_formula(sell_expr):
        buy_translated = translate_formula(buy_expr)
        sell_translated = translate_formula(sell_expr)
        translated = f"买入: {buy_translated}\n卖出: {sell_translated}"
        buy_expr = buy_translated
        sell_expr = sell_translated

    return {
        "buy_expression": buy_expr.strip(),
        "sell_expression": sell_expr.strip(),
        "translated": translated,
    }

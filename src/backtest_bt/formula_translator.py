# -*- coding: utf-8 -*-
"""通达信/同花顺公式语法 → Python 表达式翻译器。

自动检测输入是否为通达信风格公式，若是则翻译为可被 expression engine eval 的 Python 表达式。
若输入已经是 Python 表达式则原样返回。
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# 通达信特征关键字（用于自动检测）
_TDX_KEYWORDS = re.compile(
    r'\b(REF|MA|EMA|SMA|HHV|LLV|CROSS|COUNT|BARSLAST|IF)\s*\(|'
    r'\bAND\b|\bOR\b|\bNOT\b',
    re.IGNORECASE,
)

# 通达信变量映射
_VAR_MAP = {
    "C": "close", "CLOSE": "close",
    "O": "open", "OPEN": "open",
    "H": "high", "HIGH": "high",
    "L": "low", "LOW": "low",
    "V": "volume", "VOL": "volume", "VOLUME": "volume",
    "A": "amount", "AMOUNT": "amount",
}

# 匹配独立的大写变量 token（不紧跟左括号，即不是函数名）
_VAR_PATTERN = re.compile(
    r'\b(' + '|'.join(_VAR_MAP.keys()) + r')(?!\s*\()\b'
)


def _find_matching_paren(s: str, start: int) -> int:
    """从 start 位置的 '(' 开始，找到匹配的 ')' 的位置。"""
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _split_args(s: str) -> list[str]:
    """按顶层逗号分割参数字符串。"""
    args = []
    depth = 0
    current = []
    for ch in s:
        if ch == '(' or ch == '[':
            depth += 1
            current.append(ch)
        elif ch == ')' or ch == ']':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        args.append(''.join(current).strip())
    return args


def _translate_functions(expr: str) -> str:
    """递归翻译通达信函数调用。"""
    # 从内到外处理，循环直到没有更多匹配
    max_iterations = 50
    for _ in range(max_iterations):
        # 找到最内层的函数调用
        match = re.search(r'\b(REF|MA|EMA|SMA|HHV|LLV|CROSS|COUNT|BARSLAST|IF|MAX|MIN|ABS|SUM|STD)\s*\(', expr, re.IGNORECASE)
        if not match:
            break

        func_name = match.group(1).upper()
        paren_start = match.end() - 1
        paren_end = _find_matching_paren(expr, paren_start)
        if paren_end == -1:
            break

        inner = expr[paren_start + 1:paren_end]
        args = _split_args(inner)

        replacement = _translate_single_function(func_name, args)
        expr = expr[:match.start()] + replacement + expr[paren_end + 1:]

    return expr


def _translate_single_function(func_name: str, args: list[str]) -> str:
    """翻译单个通达信函数。"""
    if func_name == "REF" and len(args) >= 2:
        x = args[0]
        n = args[1].strip().lstrip('-')  # 取绝对值
        return f"({x}).shift({n})"

    if func_name == "MA" and len(args) >= 2:
        x, n = args[0], args[1]
        return f"({x}).rolling({n}).mean()"

    if func_name == "EMA" and len(args) >= 2:
        x, n = args[0], args[1]
        return f"({x}).ewm(span={n}).mean()"

    if func_name == "SMA" and len(args) >= 2:
        x, n = args[0], args[1]
        # SMA(X, N) ≈ EMA with alpha=1/N
        return f"({x}).ewm(alpha=1/{n}, adjust=False).mean()"

    if func_name == "HHV" and len(args) >= 2:
        x, n = args[0], args[1]
        return f"({x}).rolling({n}).max()"

    if func_name == "LLV" and len(args) >= 2:
        x, n = args[0], args[1]
        return f"({x}).rolling({n}).min()"

    if func_name == "SUM" and len(args) >= 2:
        x, n = args[0], args[1]
        return f"({x}).rolling({n}).sum()"

    if func_name == "STD" and len(args) >= 2:
        x, n = args[0], args[1]
        return f"({x}).rolling({n}).std()"

    if func_name == "CROSS" and len(args) >= 2:
        x, y = args[0], args[1]
        return f"(({x}).shift(1) < ({y}).shift(1)) & (({x}) > ({y}))"

    if func_name == "COUNT" and len(args) >= 2:
        cond, n = args[0], args[1]
        return f"({cond}).astype(int).rolling({n}).sum()"

    if func_name == "BARSLAST" and len(args) >= 1:
        # BARSLAST(cond) — 上一次条件成立距今的周期数，近似实现
        cond = args[0]
        return f"({cond}).astype(int).expanding().apply(lambda s: len(s) - 1 - s[::-1].argmax() if s.any() else float('nan'), raw=False)"

    if func_name == "IF" and len(args) >= 3:
        cond, a, b = args[0], args[1], args[2]
        return f"np.where({cond}, {a}, {b})"

    if func_name == "MAX" and len(args) >= 2:
        return f"np.maximum({args[0]}, {args[1]})"

    if func_name == "MIN" and len(args) >= 2:
        return f"np.minimum({args[0]}, {args[1]})"

    if func_name == "ABS" and len(args) >= 1:
        return f"np.abs({args[0]})"

    # Fallback: 不认识的函数原样返回
    return f"{func_name}({', '.join(args)})"


def is_tdx_formula(expr: str) -> bool:
    """检测表达式是否为通达信风格公式。"""
    return bool(_TDX_KEYWORDS.search(expr))


def translate_formula(expr: str) -> str:
    """将通达信公式翻译为 Python 表达式。若非通达信语法则原样返回。"""
    if not is_tdx_formula(expr):
        return expr

    result = expr

    # 1. 翻译函数调用（从内到外）
    result = _translate_functions(result)

    # 2. 替换变量名（仅替换独立 token，不替换函数名或已翻译的内容）
    def _replace_var(m: re.Match) -> str:
        return _VAR_MAP[m.group(1)]
    result = _VAR_PATTERN.sub(_replace_var, result)

    # 3. 逻辑运算符
    result = re.sub(r'\bAND\b', '&', result, flags=re.IGNORECASE)
    result = re.sub(r'\bOR\b', '|', result, flags=re.IGNORECASE)
    result = re.sub(r'\bNOT\b', '~', result, flags=re.IGNORECASE)

    # 4. 通达信的 >= <= 等比较运算符与 Python 一致，无需转换

    # 5. 折叠为单行，避免 & | 在行首导致 Python 语法错误
    result = ' '.join(result.split())

    logger.debug("Formula translated: %s → %s", expr.strip()[:80], result.strip()[:80])
    return result

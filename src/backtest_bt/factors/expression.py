# -*- coding: utf-8 -*-
"""Expression-based custom factor.

Allows users to define factors via simple Python expressions on the Web UI.
Expressions have access to: close, open, high, low, volume, amount as pd.Series,
plus common helpers like shift(), rolling(), pct_change(), etc.
"""

from __future__ import annotations

import ast
import concurrent.futures
import logging
import re
from typing import Optional

import numpy as np
import pandas as pd

from src.backtest_bt.factors.base import BaseFactor, FactorRegistry
from src.backtest_bt.formula_translator import translate_formula

logger = logging.getLogger(__name__)

# AST node whitelist — only these node types are allowed in expressions
_ALLOWED_AST_NODES = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp,
    ast.Compare, ast.IfExp, ast.Call, ast.Attribute,
    ast.Subscript, ast.Slice, ast.Index, ast.Constant, ast.Num, ast.Str,
    ast.Name, ast.Load, ast.Tuple, ast.List, ast.keyword,
    # Operators
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
    ast.BitAnd, ast.BitOr, ast.BitXor, ast.Invert,
    # Comparisons
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
}

# Allowed callable names (functions/methods users can invoke)
_ALLOWED_CALLABLES = {
    "abs", "max", "min", "sum", "mean", "std", "round", "len", "int", "float",
    "shift", "rolling", "pct_change", "diff", "cumsum", "cumprod",
    "rank", "clip", "fillna", "dropna", "replace", "where", "mask",
    "ewm", "expanding", "astype",
    "log", "log10", "sqrt", "exp", "sign", "ceil", "floor",
    "isna", "notna", "isnull", "notnull",
}

# Allowed attribute names (on pd.Series / np)
_ALLOWED_ATTRIBUTES = _ALLOWED_CALLABLES | {
    "values", "index", "iloc", "loc", "shape", "dtype", "size",
    "T", "str", "dt",
    # np functions used by formula translator
    "maximum", "minimum", "abs",
}


# Blocked attribute names — reachable via np/pd and can escape sandbox
_BLOCKED_ATTRIBUTES = {
    "sys", "os", "modules", "system", "popen", "subprocess",
    "path", "environ", "getenv",
    "__class__", "__bases__", "__subclasses__", "__mro__",
    "__globals__", "__code__", "__builtins__", "__import__",
    "__reduce__", "__reduce_ex__", "__getattr__", "__setattr__",
    "io", "common", "pickle", "marshal", "ctypes",
}


def _validate_ast(expr: str) -> Optional[str]:
    """Validate expression via AST whitelist. Returns error message or None."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        return f"语法错误: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Lambda):
            return "不允许使用 lambda 表达式"
        if type(node) not in _ALLOWED_AST_NODES:
            return f"不允许的语法: {type(node).__name__}"
        # Block dangerous attribute access
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                return f"不允许访问私有属性: {node.attr}"
            if node.attr in _BLOCKED_ATTRIBUTES:
                return f"不允许访问属性: {node.attr}"
            if node.attr not in _ALLOWED_ATTRIBUTES:
                return f"不允许的属性: {node.attr}"
        # Block dangerous function calls
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id not in _ALLOWED_CALLABLES and node.func.id not in (
                "close", "open", "high", "low", "volume", "amount",
                "np", "pd", "shift", "rolling", "pct_change",
            ):
                return f"不允许调用函数: {node.func.id}"
    return None


def validate_expression(expr: str) -> Optional[str]:
    """Validate a factor expression. Returns error message or None if valid."""
    if not expr or not expr.strip():
        return "表达式不能为空"
    if len(expr) > 1000:
        return "表达式过长（最多 1000 字符）"
    translated = translate_formula(expr)
    return _validate_ast(translated)


class ExpressionFactor(BaseFactor):
    """Factor defined by a Python expression string."""

    def __init__(self, name: str, expression: str, description: str = ""):
        self.name = name
        self.description = description or f"自定义因子: {expression}"
        self._expression = expression

    def compute(self, df: pd.DataFrame) -> pd.Series:
        # Translate formula if needed (TDX → Python)
        translated = translate_formula(self._expression)
        # Build evaluation namespace from DataFrame columns
        namespace = {
            "np": np,
            "pd": pd,
            "close": df["close"],
            "open": df["open"],
            "high": df["high"],
            "low": df["low"],
            "volume": df.get("volume", pd.Series(0, index=df.index)),
            "amount": df.get("amount", pd.Series(0, index=df.index)),
            # Convenience: shift/rolling on close by default
            "shift": df["close"].shift,
            "rolling": df["close"].rolling,
            "pct_change": df["close"].pct_change,
            "abs": abs,
            "max": max,
            "min": min,
        }
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    eval, translated, {"__builtins__": {}}, namespace  # noqa: S307
                )
                result = future.result(timeout=5)
            if isinstance(result, pd.Series):
                return result
            return pd.Series(result, index=df.index)
        except concurrent.futures.TimeoutError:
            logger.warning("Expression factor '%s' timed out (5s)", self.name)
            return pd.Series(float("nan"), index=df.index)
        except Exception as e:
            logger.warning("Expression factor '%s' failed: %s", self.name, e)
            return pd.Series(float("nan"), index=df.index)


# Storage for user-defined expression factors (in-memory, persisted via DB)
_custom_expression_factors: dict[str, dict] = {}


def register_expression_factor(name: str, expression: str, description: str = "") -> Optional[str]:
    """Register a custom expression factor. Returns error message or None."""
    error = validate_expression(expression)
    if error:
        return error
    if not name or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$", name):
        return "因子名称只能包含字母、数字和下划线，且以字母开头"

    _custom_expression_factors[name] = {
        "name": name,
        "expression": expression,
        "description": description,
    }

    # Register in the global factor registry
    factor = ExpressionFactor(name, expression, description)
    # Create a class dynamically for the registry
    factor_cls = type(
        f"Custom_{name}",
        (ExpressionFactor,),
        {"name": name, "description": description or f"自定义: {expression}"},
    )
    # Override __init__ to pass expression
    original_init = ExpressionFactor.__init__

    def custom_init(self, **kwargs):
        original_init(self, name=name, expression=expression, description=description)

    factor_cls.__init__ = custom_init
    factor_cls.name = name
    FactorRegistry._factors[name] = factor_cls

    logger.info("Registered expression factor: %s = %s", name, expression)
    return None


def list_custom_expression_factors() -> list[dict]:
    """List all user-defined expression factors."""
    return list(_custom_expression_factors.values())


def remove_expression_factor(name: str) -> bool:
    """Remove a custom expression factor."""
    if name in _custom_expression_factors:
        del _custom_expression_factors[name]
        FactorRegistry._factors.pop(name, None)
        return True
    return False

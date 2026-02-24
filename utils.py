"""ReflexiveTrader Pro — 工具函数"""

from rich.console import Console
from rich.theme import Theme

THEME = Theme({
    "title": "bold cyan",
    "profit": "bold green",
    "loss": "bold red",
    "warn": "bold yellow",
    "muted": "dim white",
    "accent": "bold magenta",
})

console = Console(theme=THEME)


def fmt_pct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    style = "profit" if value >= 0 else "loss"
    return f"[{style}]{sign}{value:.2f}%[/{style}]"


def fmt_price(value: float) -> str:
    return f"${value:,.2f}"


def fmt_r(value: float) -> str:
    style = "profit" if value >= 0 else "loss"
    sign = "+" if value >= 0 else ""
    return f"[{style}]{sign}{value:.2f}R[/{style}]"


def kelly_criterion(win_rate: float, risk_reward: float) -> float:
    """Kelly 公式: f* = (p*b - q) / b"""
    if risk_reward <= 0:
        return 0.0
    q = 1 - win_rate
    f = (win_rate * risk_reward - q) / risk_reward
    return max(0.0, f)


def calc_r_multiple(entry: float, exit_price: float, stop: float, direction: str) -> float:
    """计算 R 倍数"""
    if direction == "LONG":
        risk = entry - stop
        if risk <= 0:
            return 0.0
        return (exit_price - entry) / risk
    else:  # SHORT
        risk = stop - entry
        if risk <= 0:
            return 0.0
        return (entry - exit_price) / risk

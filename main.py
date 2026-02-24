"""ReflexiveTrader Pro — CLI 入口"""

import subprocess
import sys
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

# 确保项目根目录在 path 中
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from utils import console, fmt_pct, fmt_price, fmt_r

BANNER = """
[cyan]╔══════════════════════════════════════════════════════╗
║         REFLEXIVE TRADER PRO  v1.0                   ║
║   "Markets are always wrong. Test the fallacy."      ║
╚══════════════════════════════════════════════════════╝[/cyan]
"""


@click.group()
def cli():
    """ReflexiveTrader Pro — 反身性交易辅助系统"""
    pass


# ── new: 启动 Streamlit 决策表单 ─────────────────────────────────

@cli.command()
def new():
    """打开网页决策表单 (Streamlit)"""
    console.print(BANNER)
    console.print("[accent]正在启动决策表单...[/accent]")
    app_path = PROJECT_DIR / "input_logic.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path), "--server.headless=true"])


# ── log: Notion 记录管理 ─────────────────────────────────────────

@cli.group()
def log():
    """管理 Notion 交易记录"""
    pass


@log.command()
@click.argument("page_id")
@click.option("--status", type=click.Choice(["PLANNED", "ACTIVE", "CLOSED"]), help="更新状态")
def update(page_id, status):
    """更新交易记录状态"""
    from notion_bridge import update_trade_status
    updates = {}
    if status:
        updates["Status"] = status
    if updates:
        update_trade_status(page_id, updates)
        console.print(f"[profit]已更新 {page_id[:8]}...[/profit]")
    else:
        console.print("[warn]未指定更新内容[/warn]")


@log.command()
@click.argument("page_id")
@click.argument("exit_price", type=float)
@click.option("--notes", default="", help="退出备注")
def close(page_id, exit_price, notes):
    """关闭交易 (记录退出价)"""
    from notion_bridge import close_trade
    result = close_trade(page_id, exit_price, notes)
    console.print(f"[profit]交易已关闭[/profit]")
    console.print(f"  R-Multiple: {fmt_r(result['r_multiple'])}")
    console.print(f"  Return: {fmt_pct(result['return_pct'] * 100)}")


@log.command()
@click.argument("page_id")
@click.argument("note")
def note(page_id, note):
    """添加心理备注"""
    from notion_bridge import add_psych_note
    add_psych_note(page_id, note)
    console.print("[profit]备注已添加[/profit]")


# ── review: 复盘报告 ─────────────────────────────────────────────

@cli.command()
@click.option("--month", required=True, help="月份 (YYYY-MM)")
def review(month):
    """生成月度复盘报告"""
    console.print(BANNER)
    try:
        year, m = month.split("-")
        year, m = int(year), int(m)
    except ValueError:
        console.print("[loss]格式错误，请使用 YYYY-MM[/loss]")
        return

    from analytics_engine import generate_monthly_review
    generate_monthly_review(year, m)


# ── status: 当前持仓概览 ─────────────────────────────────────────

@cli.command()
def status():
    """查看当前活跃持仓"""
    console.print(BANNER)
    from notion_bridge import fetch_all_trades

    trades = fetch_all_trades(status="ACTIVE")
    if not trades:
        console.print("[muted]当前无活跃持仓[/muted]")
        return

    table = Table(title="ACTIVE POSITIONS", style="cyan", show_lines=True)
    table.add_column("Ticker", style="accent")
    table.add_column("Dir", width=6)
    table.add_column("Entry", justify="right")
    table.add_column("Stop", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Position", justify="right")
    table.add_column("Emotion", width=12)
    table.add_column("R/R", justify="right")

    for t in trades:
        emotion_style = "loss" if t["entry_emotion"] in {"fearful", "fomo", "fatigued"} else "profit"
        table.add_row(
            t["ticker"],
            t["direction"],
            fmt_price(t["entry_price"] or 0),
            fmt_price(t["price_stop"] or 0),
            fmt_price(t["profit_target"] or 0),
            f"{t['position_pct']:.1f}%",
            f"[{emotion_style}]{t['entry_emotion']}[/{emotion_style}]",
            f"{t['risk_reward']:.1f}" if t["risk_reward"] else "N/A",
        )

    console.print(table)


# ── config: 配置管理 ─────────────────────────────────────────────

@cli.command()
def config():
    """查看当前配置"""
    from config import load_config
    import yaml
    cfg = load_config()
    # 隐藏敏感信息
    display = cfg.copy()
    if "notion" in display:
        n = display["notion"].copy()
        if n.get("api_key") and n["api_key"] != "secret_xxx":
            n["api_key"] = n["api_key"][:10] + "..."
        display["notion"] = n
    console.print(Panel(yaml.dump(display, default_flow_style=False, allow_unicode=True), title="CONFIG", style="cyan"))


# ── 入口 ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()

"""ReflexiveTrader Pro — 模块4: 深度反身性复盘"""

from __future__ import annotations

import calendar
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from rich.panel import Panel
from rich.table import Table

from config import load_config
from notion_bridge import fetch_all_trades
from utils import calc_r_multiple, console, fmt_pct, fmt_r


# ── 统计计算 ─────────────────────────────────────────────────────

def calc_statistics(trades: list[dict]) -> dict:
    """计算核心统计指标。"""
    closed = [t for t in trades if t["status"] == "CLOSED" and t["actual_exit"] is not None]
    if not closed:
        return {"total": len(trades), "closed": 0, "win_rate": 0, "avg_r": 0,
                "best_r": 0, "worst_r": 0, "total_r": 0, "max_drawdown": 0, "r_values": []}

    wins = [t for t in closed if (t["r_multiple"] or 0) > 0]
    r_values = [t["r_multiple"] or 0 for t in closed]

    # 最大回撤 (基于累计 R)
    cumulative = pd.Series(r_values).cumsum()
    peak = cumulative.cummax()
    drawdown = cumulative - peak
    max_dd = drawdown.min()

    return {
        "total": len(trades),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(closed) - len(wins),
        "win_rate": len(wins) / len(closed) if closed else 0,
        "avg_r": sum(r_values) / len(r_values),
        "best_r": max(r_values),
        "worst_r": min(r_values),
        "total_r": sum(r_values),
        "max_drawdown": max_dd,
        "r_values": r_values,
    }


# ── 高光时刻 ─────────────────────────────────────────────────────

def find_highlights(trades: list[dict]) -> list[dict]:
    """找出 R 倍数最高且情绪冷静的交易。"""
    closed = [t for t in trades if t["status"] == "CLOSED" and t["r_multiple"] is not None]
    calm_emotions = {"calm", "confident", "exploratory"}
    highlights = [t for t in closed if t.get("entry_emotion") in calm_emotions and t["r_multiple"] > 0]
    highlights.sort(key=lambda x: x["r_multiple"], reverse=True)
    return highlights[:5]


# ── 错误指纹 ─────────────────────────────────────────────────────

def find_error_fingerprints(trades: list[dict]) -> dict:
    """分析亏损单的时间段和情绪模式。"""
    losers = [t for t in trades if t["status"] == "CLOSED" and (t["r_multiple"] or 0) < 0]
    if not losers:
        return {"by_emotion": {}, "by_period": {}, "patterns": []}

    # 按情绪分组
    by_emotion = defaultdict(list)
    for t in losers:
        by_emotion[t.get("entry_emotion", "unknown")].append(t["r_multiple"])

    emotion_stats = {k: {"count": len(v), "avg_r": sum(v) / len(v), "total_r": sum(v)}
                     for k, v in by_emotion.items()}

    # 按时间段分组 (基于创建时间的小时)
    by_period = defaultdict(list)
    for t in losers:
        created = t.get("created", "")
        if created:
            try:
                hour = pd.Timestamp(created).hour
                if hour < 10:
                    period = "开盘 (pre-10)"
                elif hour < 14:
                    period = "盘中 (10-14)"
                elif hour < 16:
                    period = "收盘前 (14-16)"
                else:
                    period = "盘后 (16+)"
                by_period[period].append(t["r_multiple"])
            except Exception:
                pass

    period_stats = {k: {"count": len(v), "avg_r": sum(v) / len(v)}
                    for k, v in by_period.items()}

    # 识别模式
    patterns = []
    for emotion, stats in emotion_stats.items():
        if stats["count"] >= 2:
            patterns.append(f"在 {emotion} 情绪下有 {stats['count']} 笔亏损 (平均 {stats['avg_r']:.2f}R)")
    for period, stats in period_stats.items():
        if stats["count"] >= 2:
            patterns.append(f"在 {period} 时段有 {stats['count']} 笔亏损 (平均 {stats['avg_r']:.2f}R)")

    return {"by_emotion": emotion_stats, "by_period": period_stats, "patterns": patterns}


# ── 纪律评分 ─────────────────────────────────────────────────────

def calc_discipline_score(trades: list[dict]) -> dict:
    """比较计划价与实际执行的偏差。"""
    closed = [t for t in trades if t["status"] == "CLOSED"
              and t["entry_price"] and t["actual_exit"] and t["profit_target"]]
    if not closed:
        return {"score": 100, "avg_deviation": 0, "details": []}

    deviations = []
    for t in closed:
        dev = abs((t["deviation_pct"] or 0))
        deviations.append({"ticker": t["ticker"], "deviation": dev})

    avg_dev = sum(d["deviation"] for d in deviations) / len(deviations)
    score = max(0, 100 - avg_dev * 100)

    return {"score": score, "avg_deviation": avg_dev, "details": deviations}


# ── 深度分析 ─────────────────────────────────────────────────────

def deep_analysis(trades: list[dict]) -> dict:
    """区分'市场对 vs 假设对'，识别执行力偏差。"""
    closed = [t for t in trades if t["status"] == "CLOSED" and t["r_multiple"] is not None]
    if not closed:
        return {"market_vs_thesis": [], "execution_gaps": []}

    analysis = []
    for t in closed:
        r = t["r_multiple"]
        emotion = t.get("entry_emotion", "")
        familiarity = t.get("familiarity", 5)
        deviation = t.get("deviation_pct", 0) or 0

        if r > 0 and familiarity and familiarity <= 3:
            analysis.append(f"{t['ticker']}: 盈利但熟悉度低 ({familiarity}/10) — 可能是市场顺风而非假设正确")
        elif r < 0 and familiarity and familiarity >= 7:
            analysis.append(f"{t['ticker']}: 亏损但熟悉度高 ({familiarity}/10) — 假设可能有盲点")
        if deviation > 0.05:
            analysis.append(f"{t['ticker']}: 执行偏差 {deviation:.1%} — 纪律需加强")

    return {"insights": analysis}


# ── 仓位分布分析 ─────────────────────────────────────────────────

def calc_position_analysis(trades: list[dict]) -> dict:
    """分析仓位分布和个股收益。"""
    # 仓位分布 — 按标的聚合 (非 CLOSED 的持仓)
    active_trades = [t for t in trades if t["status"] in ("PLANNED", "ACTIVE")]
    by_ticker_pos = defaultdict(lambda: {"position_pct": 0, "status": "", "direction": ""})
    for t in active_trades:
        entry = by_ticker_pos[t["ticker"]]
        entry["position_pct"] += t["position_pct"]
        entry["status"] = t["status"]
        entry["direction"] = t["direction"]

    position_dist = [
        {"ticker": k, "position_pct": v["position_pct"],
         "status": v["status"], "direction": v["direction"]}
        for k, v in by_ticker_pos.items()
    ]
    position_dist.sort(key=lambda x: x["position_pct"], reverse=True)

    total_position = sum(p["position_pct"] for p in position_dist)
    # 集中度: 最大单标的占总仓位比例
    max_concentration = (position_dist[0]["position_pct"] / total_position * 100) if position_dist and total_position > 0 else 0

    # 个股收益统计 (仅已关闭)
    closed = [t for t in trades if t["status"] == "CLOSED" and t["r_multiple"] is not None]
    by_ticker = defaultdict(list)
    for t in closed:
        by_ticker[t["ticker"]].append(t)

    ticker_stats = {}
    for ticker, ticker_trades in by_ticker.items():
        wins = [t for t in ticker_trades if t["r_multiple"] > 0]
        r_vals = [t["r_multiple"] for t in ticker_trades]
        returns = [t.get("actual_return_pct", 0) or 0 for t in ticker_trades]
        ticker_stats[ticker] = {
            "trades": len(ticker_trades),
            "wins": len(wins),
            "win_rate": len(wins) / len(ticker_trades),
            "avg_r": sum(r_vals) / len(r_vals),
            "total_r": sum(r_vals),
            "avg_return": sum(returns) / len(returns),
            "total_return": sum(returns),
        }

    # 总账户收益 (加权)
    total_weighted_return = 0
    for t in closed:
        ret = t.get("actual_return_pct", 0) or 0
        pos = t.get("position_pct", 0) or 0
        total_weighted_return += ret * (pos / 100)

    return {
        "position_dist": position_dist,
        "total_position": total_position,
        "max_concentration": max_concentration,
        "ticker_stats": ticker_stats,
        "total_weighted_return": total_weighted_return,
    }


# ── 风险偏好评分 ─────────────────────────────────────────────────

def calc_risk_profile(trades: list[dict]) -> dict:
    """基于建仓参数分析风险偏好。
    评分 0-100: 0=极度保守, 50=均衡, 100=极度激进
    """
    if not trades:
        return {"score": 50, "label": "数据不足", "factors": []}

    factors = []

    # 1. 平均仓位 (权重 30%) — 仓位越大越激进
    avg_pos = sum(t["position_pct"] for t in trades) / len(trades)
    max_pos = max(t["position_pct"] for t in trades)
    # 仓位 2% 以下保守, 5% 中性, 10%+ 激进
    pos_score = min(100, max(0, (avg_pos - 1) / 14 * 100))
    factors.append({
        "name": "平均仓位",
        "value": f"{avg_pos:.1f}%",
        "detail": f"最大 {max_pos:.1f}%",
        "score": pos_score,
        "weight": 0.30,
    })

    # 2. 平均盈亏比 (权重 25%) — 盈亏比越低越激进 (追求高频小利)
    rr_values = [t["risk_reward"] for t in trades if t.get("risk_reward")]
    if rr_values:
        avg_rr = sum(rr_values) / len(rr_values)
        # R/R < 1 激进, 2 中性, 4+ 保守
        rr_score = min(100, max(0, 100 - (avg_rr - 0.5) / 4 * 100))
        factors.append({
            "name": "平均盈亏比",
            "value": f"{avg_rr:.1f}",
            "detail": f"{'偏低 (高频)' if avg_rr < 1.5 else '偏高 (精选)' if avg_rr > 3 else '均衡'}",
            "score": rr_score,
            "weight": 0.25,
        })

    # 3. 平均预期胜率 (权重 20%) — 低胜率+高赔率=激进; 高胜率+低赔率=保守
    wr_values = [t["win_rate"] for t in trades if t.get("win_rate")]
    if wr_values:
        avg_wr = sum(wr_values) / len(wr_values)
        # 胜率 < 40% 激进, 50% 中性, 70%+ 保守
        wr_score = min(100, max(0, 100 - (avg_wr - 0.2) / 0.6 * 100))
        factors.append({
            "name": "平均预期胜率",
            "value": f"{avg_wr:.0%}",
            "detail": f"{'低胜率高赔率' if avg_wr < 0.4 else '高胜率低赔率' if avg_wr > 0.6 else '均衡'}",
            "score": wr_score,
            "weight": 0.20,
        })

    # 4. Kelly 利用率 (权重 15%) — 实际仓位 vs Kelly 建议
    kelly_ratios = []
    for t in trades:
        wr = t.get("win_rate", 0)
        rr = t.get("risk_reward", 0)
        if wr and rr and wr > 0 and rr > 0:
            kelly = (wr * rr - (1 - wr)) / rr
            if kelly > 0:
                actual_ratio = (t["position_pct"] / 100) / kelly
                kelly_ratios.append(actual_ratio)
    if kelly_ratios:
        avg_kelly_ratio = sum(kelly_ratios) / len(kelly_ratios)
        # < 0.3 保守, 0.5 中性 (半Kelly), 1.0+ 激进
        kelly_score = min(100, max(0, avg_kelly_ratio / 1.5 * 100))
        factors.append({
            "name": "Kelly 利用率",
            "value": f"{avg_kelly_ratio:.0%}",
            "detail": f"{'< 半Kelly (保守)' if avg_kelly_ratio < 0.4 else '> 全Kelly (激进)' if avg_kelly_ratio > 1.0 else '半Kelly 附近'}",
            "score": kelly_score,
            "weight": 0.15,
        })

    # 5. 交易频率密度 (权重 10%) — 交易越频繁越激进
    freq_score = min(100, max(0, len(trades) / 20 * 100))
    factors.append({
        "name": "交易频率",
        "value": f"{len(trades)} 笔/月",
        "detail": f"{'低频' if len(trades) <= 5 else '高频' if len(trades) >= 15 else '中频'}",
        "score": freq_score,
        "weight": 0.10,
    })

    # 加权总分
    total_weight = sum(f["weight"] for f in factors)
    weighted_score = sum(f["score"] * f["weight"] for f in factors) / total_weight if total_weight else 50

    # 标签
    if weighted_score >= 75:
        label = "激进型 🔥"
    elif weighted_score >= 55:
        label = "偏激进 ⚡"
    elif weighted_score >= 45:
        label = "均衡型 ⚖️"
    elif weighted_score >= 25:
        label = "偏保守 🛡️"
    else:
        label = "保守型 🏦"

    return {"score": weighted_score, "label": label, "factors": factors}


# ── 改进建议 ─────────────────────────────────────────────────────

def generate_suggestions(fingerprints: dict, discipline: dict, risk_profile: dict | None = None) -> list[str]:
    """基于错误指纹生成行动指令。"""
    suggestions = []

    emotion_stats = fingerprints.get("by_emotion", {})
    if "fomo" in emotion_stats and emotion_stats["fomo"]["count"] >= 2:
        suggestions.append("ACTION: 在 FOMO 状态下将仓位上限降至正常的 50%")
    if "fatigued" in emotion_stats and emotion_stats["fatigued"]["count"] >= 1:
        suggestions.append("ACTION: 疲惫时禁止开仓，先休息再决策")
    if "fearful" in emotion_stats and emotion_stats["fearful"]["count"] >= 2:
        suggestions.append("ACTION: 恐惧情绪下的交易亏损率高，建议暂停并重新评估假设")

    period_stats = fingerprints.get("by_period", {})
    for period, stats in period_stats.items():
        if stats["count"] >= 2:
            suggestions.append(f"ACTION: 减少在 {period} 时段的交易频率")

    if discipline.get("score", 100) < 80:
        suggestions.append("ACTION: 纪律评分偏低，建议严格按计划执行，减少临时决策")

    if risk_profile:
        score = risk_profile.get("score", 50)
        if score >= 75:
            suggestions.append("ACTION: 风险偏好偏激进 — 建议降低平均仓位或提高胜率门槛")
        elif score <= 25:
            suggestions.append("INFO: 风险偏好偏保守 — 可适当提高盈亏比要求以匹配保守风格")

    if not suggestions:
        suggestions.append("本月表现稳定，继续保持当前纪律。")

    return suggestions


# ── Plotly HTML 报告 ─────────────────────────────────────────────

def render_html_report(review: dict, output_path: str) -> str:
    """生成 Plotly 交互式 HTML 报告。"""
    stats = review["statistics"]
    fingerprints = review["fingerprints"]
    position_analysis = review.get("position_analysis", {})
    risk_profile = review.get("risk_profile", {})

    fig = make_subplots(
        rows=5, cols=2,
        subplot_titles=(
            "R-Multiple 分布", "累计 R 曲线",
            "情绪 × R-Multiple", "纪律评分",
            "仓位分布 (按标的)", "个股收益 (R-Multiple)",
            "风险偏好雷达", "错误指纹: 情绪分布",
            "错误指纹: 时段分布", "",
        ),
        specs=[
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy"}, {"type": "indicator"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "polar"}, {"type": "xy"}],
            [{"type": "xy"}, None],
        ],
        vertical_spacing=0.08,
        horizontal_spacing=0.1,
    )

    r_values = stats.get("r_values", [])

    # 1. R-Multiple 分布直方图
    if r_values:
        colors = ["#00C853" if r > 0 else "#FF1744" for r in r_values]
        fig.add_trace(go.Bar(x=list(range(len(r_values))), y=r_values,
                             marker_color=colors, name="R-Multiple"), row=1, col=1)

    # 2. 累计 R 曲线
    if r_values:
        cum_r = pd.Series(r_values).cumsum().tolist()
        fig.add_trace(go.Scatter(y=cum_r, mode="lines+markers", name="Cumulative R",
                                 line=dict(color="#00BCD4", width=2)), row=1, col=2)

    # 3. 情绪-收益散点图
    trades = review.get("trades", [])
    closed = [t for t in trades if t["status"] == "CLOSED" and t["r_multiple"] is not None]
    if closed:
        emotions = [t.get("entry_emotion", "unknown") for t in closed]
        r_vals = [t["r_multiple"] for t in closed]
        scatter_colors = ["#00C853" if r > 0 else "#FF1744" for r in r_vals]
        fig.add_trace(go.Scatter(
            x=emotions, y=r_vals, mode="markers",
            marker=dict(size=12, color=scatter_colors, opacity=0.7),
            name="Emotion vs R",
        ), row=2, col=1)

    # 4. 纪律评分
    discipline = review.get("discipline", {})
    score = discipline.get("score", 100)
    fig.add_trace(go.Indicator(
        mode="gauge+number", value=score,
        gauge=dict(
            axis=dict(range=[0, 100]),
            bar=dict(color="#00BCD4"),
            steps=[
                dict(range=[0, 60], color="#FF1744"),
                dict(range=[60, 80], color="#FFC107"),
                dict(range=[80, 100], color="#00C853"),
            ],
        ),
    ), row=2, col=2)

    # 5. 仓位分布 (按标的聚合)
    pos_dist = position_analysis.get("position_dist", [])
    if pos_dist:
        tickers = [p["ticker"] for p in pos_dist]
        positions = [p["position_pct"] for p in pos_dist]
        status_colors = {"PLANNED": "#FFC107", "ACTIVE": "#00BCD4", "CLOSED": "#607d8b"}
        bar_colors = [status_colors.get(p["status"], "#607d8b") for p in pos_dist]
        fig.add_trace(go.Bar(
            x=tickers, y=positions, marker_color=bar_colors, name="Position %",
            text=[f"{p:.1f}%" for p in positions], textposition="auto",
        ), row=3, col=1)

    # 6. 个股收益 (R-Multiple)
    ticker_stats = position_analysis.get("ticker_stats", {})
    if ticker_stats:
        t_names = list(ticker_stats.keys())
        t_r = [v["total_r"] for v in ticker_stats.values()]
        t_colors = ["#00C853" if r > 0 else "#FF1744" for r in t_r]
        fig.add_trace(go.Bar(
            x=t_names, y=t_r, marker_color=t_colors, name="Total R by Ticker",
            text=[f"{r:.2f}R" for r in t_r], textposition="auto",
        ), row=3, col=2)

    # 7. 风险偏好雷达图
    risk_factors = risk_profile.get("factors", [])
    if risk_factors:
        categories = [f["name"] for f in risk_factors]
        values = [f["score"] for f in risk_factors]
        categories.append(categories[0])
        values.append(values[0])
        fig.add_trace(go.Scatterpolar(
            r=values, theta=categories, fill="toself",
            fillcolor="rgba(0, 188, 212, 0.2)",
            line=dict(color="#00BCD4", width=2),
            name="Risk Profile",
        ), row=4, col=1)

    # 8. 错误指纹: 情绪
    emo_stats = fingerprints.get("by_emotion", {})
    if emo_stats:
        fig.add_trace(go.Bar(
            x=list(emo_stats.keys()),
            y=[v["count"] for v in emo_stats.values()],
            marker_color="#FF1744", name="Loss by Emotion",
        ), row=4, col=2)

    # 9. 错误指纹: 时段
    period_stats = fingerprints.get("by_period", {})
    if period_stats:
        fig.add_trace(go.Bar(
            x=list(period_stats.keys()),
            y=[v["count"] for v in period_stats.values()],
            marker_color="#FF9800", name="Loss by Period",
        ), row=5, col=1)

    # 样式
    fig.update_layout(
        title=dict(text=f"ReflexiveTrader Pro — Monthly Review ({review['period']})", font=dict(size=20)),
        template="plotly_dark",
        height=2000,
        showlegend=False,
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#16213e",
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    return output_path


# ── 终端摘要 ─────────────────────────────────────────────────────

def print_terminal_summary(review: dict) -> None:
    """在终端打印复盘摘要。"""
    stats = review["statistics"]
    discipline = review["discipline"]
    highlights = review["highlights"]
    fingerprints = review["fingerprints"]
    suggestions = review["suggestions"]
    deep = review["deep_analysis"]

    # 统计表
    table = Table(title=f"MONTHLY REVIEW — {review['period']}", style="cyan", show_lines=True)
    table.add_column("Metric", style="accent", width=20)
    table.add_column("Value", width=20)

    table.add_row("Total Trades", str(stats["total"]))
    table.add_row("Closed", str(stats.get("closed", 0)))
    table.add_row("Win Rate", fmt_pct(stats.get("win_rate", 0) * 100))
    table.add_row("Avg R", fmt_r(stats.get("avg_r", 0)))
    table.add_row("Best R", fmt_r(stats.get("best_r", 0)))
    table.add_row("Worst R", fmt_r(stats.get("worst_r", 0)))
    table.add_row("Total R", fmt_r(stats.get("total_r", 0)))
    table.add_row("Max Drawdown", fmt_r(stats.get("max_drawdown", 0)))
    table.add_row("Discipline", f"{discipline.get('score', 100):.0f}/100")
    console.print(table)

    # 高光时刻
    if highlights:
        console.print(Panel("[title]HIGHLIGHTS[/title]", style="green"))
        for h in highlights:
            console.print(f"  [profit]{h['ticker']}[/profit] {fmt_r(h['r_multiple'])} | {h.get('entry_emotion', '')} | {h.get('thesis', '')[:60]}")

    # 错误指纹
    if fingerprints["patterns"]:
        console.print(Panel("[title]ERROR FINGERPRINTS[/title]", style="red"))
        for p in fingerprints["patterns"]:
            console.print(f"  [loss]{p}[/loss]")

    # 深度分析
    if deep.get("insights"):
        console.print(Panel("[title]DEEP ANALYSIS[/title]", style="yellow"))
        for insight in deep["insights"]:
            console.print(f"  [warn]{insight}[/warn]")

    # 建议
    console.print(Panel("[title]ACTION ITEMS[/title]", style="cyan"))
    for s in suggestions:
        console.print(f"  [accent]{s}[/accent]")


# ── 主函数 ───────────────────────────────────────────────────────

def generate_monthly_review(year: int, month: int) -> dict:
    """生成月度复盘报告。"""
    _, last_day = calendar.monthrange(year, month)
    start = f"{year}-{month:02d}-01T00:00:00Z"
    end = f"{year}-{month:02d}-{last_day}T23:59:59Z"
    period = f"{year}-{month:02d}"

    console.print(f"[muted]正在从 Notion 拉取 {period} 的交易记录...[/muted]")
    trades = fetch_all_trades(date_range=(start, end))

    if not trades:
        console.print("[warn]该月无交易记录。[/warn]")
        return {"period": period, "trades": [], "statistics": {"total": 0}}

    stats = calc_statistics(trades)
    highlights = find_highlights(trades)
    fingerprints = find_error_fingerprints(trades)
    discipline = calc_discipline_score(trades)
    deep = deep_analysis(trades)
    suggestions = generate_suggestions(fingerprints, discipline)

    review = {
        "period": period,
        "trades": trades,
        "statistics": stats,
        "highlights": highlights,
        "fingerprints": fingerprints,
        "discipline": discipline,
        "deep_analysis": deep,
        "suggestions": suggestions,
    }

    # 终端摘要
    print_terminal_summary(review)

    # HTML 报告
    cfg = load_config()
    output_dir = cfg.get("reports", {}).get("output_dir", "./reports")
    output_path = f"{output_dir}/{period}_review.html"
    render_html_report(review, output_path)
    console.print(f"\n[profit]HTML 报告已生成: {output_path}[/profit]")

    return review

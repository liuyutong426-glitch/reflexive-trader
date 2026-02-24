"""ReflexiveTrader Pro — Streamlit 多页面应用"""

import sys
import os
import calendar
import tempfile
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

# ── 页面配置（必须在最前面，只能调用一次）──────────────────────

LOGO_FILENAME = "Gemini_Generated_Image_ogzugqogzugqogzu.png"
logo_path = os.path.join(os.path.dirname(__file__), LOGO_FILENAME)

if os.path.exists(logo_path):
    st.set_page_config(
        page_title="ReflexiveTrader Pro",
        page_icon=logo_path,
        layout="wide",
    )
    st.logo(logo_path)
else:
    st.set_page_config(
        page_title="ReflexiveTrader Pro",
        page_icon="📊",
        layout="wide",
    )

sys.path.insert(0, str(Path(__file__).parent))

from models import (
    EXTREME_EMOTIONS,
    InvalidationPlan,
    PositionPlan,
    PsychologyCheck,
    TradeHypothesis,
    TradePlan,
)
from utils import kelly_criterion

# ── 自定义样式 ───────────────────────────────────────────────────

# PWA 配置 - 让手机可以添加到桌面（使用 base64 嵌入图标）
try:
    from generate_pwa_html import PWA_HTML
    st.markdown(PWA_HTML, unsafe_allow_html=True)
except Exception:
    # Fallback: 使用相对路径（可能在某些环境不工作）
    st.markdown("""
    <link rel="manifest" href="./manifest.json">
    <meta name="theme-color" content="#00bcd4">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="ReflexiveTrader">
    <link rel="apple-touch-icon" href="./apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="192x192" href="./icon-192.png">
    <link rel="shortcut icon" href="./favicon.ico">
    """, unsafe_allow_html=True)

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .block-container { max-width: 900px; padding-top: 2rem; }
    h1 { color: #00bcd4; text-align: center; }
    h2 { color: #00bcd4; border-bottom: 1px solid #1e3a5f; padding-bottom: 0.3rem; }
    .stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── 侧边栏导航 ──────────────────────────────────────────────────

page = st.sidebar.radio("导航", ["📝 新建交易计划", "📋 管理持仓", "📊 月度复盘"], index=0)

st.markdown("# REFLEXIVE TRADER PRO")
st.markdown(
    '<p style="text-align:center;color:#607d8b;">'
    '"Markets are always wrong. Test the fallacy."</p>',
    unsafe_allow_html=True,
)
# ── PLACEHOLDER_PAGES ──

# =====================================================================
# PAGE 1: 新建交易计划
# =====================================================================
if page == "📝 新建交易计划":
    st.divider()
    st.markdown("## 1. 核心假设")

    col1, col2 = st.columns([2, 1])
    with col1:
        ticker = st.text_input("标的代码", placeholder="AAPL").upper().strip()
    with col2:
        DIRECTION_OPTIONS = {
            "LONG": "🟢 做多",
            "SHORT": "🔴 做空",
        }
        direction = st.selectbox(
            "方向",
            options=list(DIRECTION_OPTIONS.keys()),
            format_func=lambda x: DIRECTION_OPTIONS[x],
        )

    thesis = st.text_area("投资逻辑 (核心假设)", placeholder="描述你的建仓逻辑...", height=100)

    col_k, col_u, col_p = st.columns(3)
    with col_k:
        known_factors = st.text_area("你知道什么", placeholder="已确认的信息...", height=80)
    with col_u:
        unknown_factors = st.text_area("你不知道什么", placeholder="不确定的因素...", height=80)
    with col_p:
        priced_in = st.text_area("是否已 Price In", placeholder="市场是否已反映...", height=80)

    familiarity = st.slider("熟悉度评分", 1, 10, 5, help="1=完全不了解, 10=深度研究")
    if familiarity <= 3:
        st.warning("⚠️ 熟悉度较低 — 建议缩小仓位或进一步研究")

    technical_confirmed = st.checkbox("✅ 已确认技术面 (操作前是否看过技术图？)", value=False)
    if not technical_confirmed:
        st.info("💡 建议在操作前确认技术面走势，避免逆势交易")

    st.divider()
    st.markdown("## 2. 失效点与盈利目标")
# ── PLACEHOLDER_STEP2 ──

    col_e, col_s = st.columns(2)
    with col_e:
        entry_price = st.number_input("计划入场价", min_value=0.01, value=100.0, step=0.01, format="%.2f")
    with col_s:
        price_stop = st.number_input("价格止损", min_value=0.01, value=90.0, step=0.01, format="%.2f")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        profit_target_1 = st.number_input("第一盈利目标", min_value=0.01, value=120.0, step=0.01, format="%.2f")
    with col_t2:
        profit_target_2 = st.number_input("第二盈利目标 (加仓点)", min_value=0.0, value=0.0, step=0.01, format="%.2f")

    col_ts, col_act = st.columns(2)
    with col_ts:
        time_stop = st.date_input("时间止损", value=date.today() + timedelta(days=30))
    with col_act:
        action_at_target = st.selectbox("达到目标后操作", ["TAKE_PROFIT", "PYRAMID", "HOLD"])

    logic_stop = st.text_input("逻辑止损 (什么情况下假设失效？)", placeholder="例: 财报不及预期 / 管理层变动...")

    st.divider()
    st.markdown("## 3. 心理状态自评")

    EMOTION_OPTIONS = {
        "calm": "😌 冷静", "confident": "💪 自信", "exploratory": "🔍 尝试",
        "fearful": "😰 恐惧", "fomo": "🔥 FOMO", "fatigued": "😴 疲惫",
    }
    emotion = st.selectbox("当前情绪状态", options=list(EMOTION_OPTIONS.keys()),
                           format_func=lambda x: EMOTION_OPTIONS[x], index=0)

    is_extreme = emotion in EXTREME_EMOTIONS
    if is_extreme:
        st.error(f"🚨 **EXTREME EMOTION DETECTED**\n\n当前情绪: **{EMOTION_OPTIONS[emotion]}**\n\n建议暂停 15 分钟后重新评估。")

    psych_note = st.text_input("补充说明 (可选)", placeholder="当前心理状态的额外备注...")

    st.divider()
    st.markdown("## 4. 仓位与盈亏比")
# ── PLACEHOLDER_STEP4 ──

    col_w, col_rr = st.columns(2)
    with col_w:
        win_rate_pct = st.slider("预期胜率", 5, 95, 50, 5, format="%d%%",
                                  help="你认为这笔交易盈利的概率")
        win_rate = win_rate_pct / 100
    with col_rr:
        risk_reward = st.number_input("盈亏比 (盈利/亏损)", min_value=0.1, value=2.0, step=0.1, format="%.1f")

    kelly = kelly_criterion(win_rate, risk_reward)
    risk_per_share = abs(entry_price - price_stop)

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Kelly 建议仓位", f"{kelly:.1%}")
    with col_info2:
        st.metric("半 Kelly", f"{kelly/2:.1%}")
    with col_info3:
        st.metric("每股风险", f"${risk_per_share:.2f}")

    position_pct = st.number_input("实际仓位 (占总资金 %)", min_value=0.1, max_value=100.0,
                                   value=min(max(round(kelly * 50, 1), 0.1), 100.0), step=0.5, format="%.1f")

    st.divider()
    st.markdown("## 交易计划摘要")

    if ticker:
        summary_data = {
            "标的": f"{ticker} ({DIRECTION_OPTIONS[direction]})",
            "技术面": "✅ 已确认" if technical_confirmed else "❌ 未确认",
            "入场价": f"${entry_price:.2f}", "止损": f"${price_stop:.2f}",
            "目标1": f"${profit_target_1:.2f}",
            "目标2": f"${profit_target_2:.2f}" if profit_target_2 else "N/A",
            "时间止损": str(time_stop), "情绪": EMOTION_OPTIONS[emotion],
            "胜率": f"{win_rate:.0%}", "盈亏比": f"{risk_reward:.1f}", "仓位": f"{position_pct:.1f}%",
        }
        cols = st.columns(4)
        for i, (k, v) in enumerate(summary_data.items()):
            with cols[i % 4]:
                st.markdown(f"**{k}**<br>{v}", unsafe_allow_html=True)

    st.divider()

    can_submit = bool(ticker and thesis and entry_price > 0 and price_stop > 0)
    if is_extreme:
        confirm_extreme = st.checkbox("I confirm to proceed under extreme emotion", value=False)
        can_submit = can_submit and confirm_extreme

    submitted = st.button("提交交易计划并同步到 Notion", type="primary",
                          disabled=not can_submit, use_container_width=True)

    if submitted:
        hypothesis = TradeHypothesis(ticker=ticker, direction=direction, thesis=thesis,
            familiarity_score=familiarity, known_factors=known_factors,
            unknown_factors=unknown_factors, priced_in=priced_in, technical_confirmed=technical_confirmed)
        invalidation = InvalidationPlan(price_stop=price_stop, time_stop=str(time_stop),
            logic_stop=logic_stop, profit_target_1=profit_target_1,
            profit_target_2=profit_target_2, action_at_target=action_at_target)
        psychology = PsychologyCheck(emotion=emotion, is_extreme=is_extreme, note=psych_note)
        position = PositionPlan(win_rate=win_rate, risk_reward=risk_reward,
            position_pct=position_pct, entry_price=entry_price)
        plan = TradePlan(hypothesis=hypothesis, invalidation=invalidation,
            psychology=psychology, position=position)
        try:
            from notion_bridge import sync_trade_plan
            page_id = sync_trade_plan(plan)
            st.success(f"Done! Synced to Notion (page: {page_id[:8]}...)")
            st.balloons()
        except Exception as e:
            st.error(f"Notion sync failed: {e}")

# =====================================================================
# PAGE 2: 管理持仓
# =====================================================================
elif page == "📋 管理持仓":
    st.divider()
    st.markdown("## 持仓管理")

    from notion_bridge import fetch_all_trades, close_trade, update_trade_status, add_psych_note

    STATUS_FILTER = st.selectbox("筛选状态", ["ALL", "PLANNED", "ACTIVE", "CLOSED"], index=0)

    try:
        with st.spinner("正在从 Notion 拉取交易记录..."):
            if STATUS_FILTER == "ALL":
                trades = fetch_all_trades()
            else:
                trades = fetch_all_trades(status=STATUS_FILTER)
    except Exception as e:
        st.error(f"Notion 连接失败，请稍后重试: {e}")
        trades = []

    if not trades:
        st.info("暂无交易记录")
    else:
        st.markdown(f"共 **{len(trades)}** 条记录")

        for idx, t in enumerate(trades):
            status_emoji = {"PLANNED": "⏳", "ACTIVE": "🟢", "CLOSED": "✅"}.get(t["status"], "❓")
            r_display = f" | R: {t['r_multiple']:.2f}" if t["r_multiple"] is not None else ""
            with st.expander(
                f"{status_emoji} **{t['ticker']}** — {t['direction']} | "
                f"入场 ${t['entry_price']:.2f} | 止损 ${t['price_stop']:.2f} | "
                f"状态: {t['status']}{r_display}"
            ):
                # 交易详情
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("入场价", f"${t['entry_price']:.2f}")
                c2.metric("止损", f"${t['price_stop']:.2f}")
                c3.metric("目标", f"${t['profit_target']:.2f}" if t["profit_target"] else "N/A")
                c4.metric("仓位", f"{t['position_pct']:.1f}%")

                if t["thesis"]:
                    st.caption(f"假设: {t['thesis'][:120]}")

                # ── 操作区 ──
                if t["status"] != "CLOSED":
                    st.markdown("---")
                    action_tabs = st.tabs(["平仓", "加仓", "减仓", "更新状态", "添加备注"])

                    # Tab 1: 平仓 (全部退出)
                    with action_tabs[0]:
                        col_exit, col_note = st.columns([1, 2])
                        with col_exit:
                            exit_price = st.number_input(
                                "退出价格", min_value=0.01, value=float(t["entry_price"]),
                                step=0.01, format="%.2f", key=f"exit_{idx}")
                        with col_note:
                            close_notes = st.text_input(
                                "退出备注 (可选)", placeholder="退出原因...",
                                key=f"close_note_{idx}")

                        if st.button("确认平仓", key=f"close_{idx}", type="primary"):
                            try:
                                result = close_trade(t["page_id"], exit_price, close_notes)
                                st.success(
                                    f"交易已关闭! R-Multiple: {result['r_multiple']:.2f} | "
                                    f"收益: {result['return_pct']:.2%}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"平仓失败: {e}")

                    # Tab 2: 加仓 (加码摊平)
                    with action_tabs[1]:
                        col_ap, col_apct = st.columns(2)
                        with col_ap:
                            add_price = st.number_input(
                                "加仓价格", min_value=0.01, value=float(t["entry_price"]),
                                step=0.01, format="%.2f", key=f"add_price_{idx}")
                        with col_apct:
                            add_pct = st.number_input(
                                "加仓仓位 (占总资金 %)", min_value=0.1, max_value=100.0,
                                value=min(t["position_pct"], 50.0), step=0.5, format="%.1f",
                                key=f"add_pct_{idx}")
                        add_reason = st.text_input(
                            "加仓原因", placeholder="为什么加仓...",
                            key=f"add_reason_{idx}")

                        old_pos = t["position_pct"]
                        new_pos = old_pos + add_pct
                        new_cost = (t["entry_price"] * old_pos + add_price * add_pct) / new_pos
                        st.caption(
                            f"仓位: {old_pos:.1f}% → {new_pos:.1f}% | "
                            f"成本: ${t['entry_price']:.2f} → ${new_cost:.2f}")

                        if st.button("确认加仓", key=f"add_{idx}", type="primary"):
                            try:
                                note_text = (
                                    f"[加仓] 价格 ${add_price:.2f} | "
                                    f"加仓 {add_pct:.1f}% | "
                                    f"仓位 {old_pos:.1f}% → {new_pos:.1f}% | "
                                    f"成本 ${t['entry_price']:.2f} → ${new_cost:.2f}"
                                )
                                if add_reason:
                                    note_text += f" | 原因: {add_reason}"
                                add_psych_note(t["page_id"], note_text)
                                update_trade_status(t["page_id"], {
                                    "Entry Price": round(new_cost, 2),
                                    "Position %": new_pos / 100,
                                })
                                st.success(
                                    f"加仓成功! 成本 ${new_cost:.2f} | 仓位 {new_pos:.1f}%")
                                st.rerun()
                            except Exception as e:
                                st.error(f"加仓失败: {e}")

                    # Tab 3: 减仓 (部分退出)
                    with action_tabs[2]:
                        col_rp, col_rpct = st.columns(2)
                        with col_rp:
                            reduce_price = st.number_input(
                                "减仓价格", min_value=0.01, value=float(t["entry_price"]),
                                step=0.01, format="%.2f", key=f"reduce_price_{idx}")
                        with col_rpct:
                            reduce_pct = st.slider(
                                "减仓比例", 10, 90, 50, 10,
                                format="%d%%", key=f"reduce_pct_{idx}",
                                help="减掉当前仓位的百分比")
                        reduce_reason = st.text_input(
                            "减仓原因", placeholder="为什么减仓...",
                            key=f"reduce_reason_{idx}")

                        new_position = t["position_pct"] * (1 - reduce_pct / 100)
                        st.caption(f"仓位变化: {t['position_pct']:.1f}% → {new_position:.1f}%")

                        if st.button("确认减仓", key=f"reduce_{idx}", type="primary"):
                            try:
                                note_text = (
                                    f"[减仓] 价格 ${reduce_price:.2f} | "
                                    f"减仓 {reduce_pct}% | "
                                    f"仓位 {t['position_pct']:.1f}% → {new_position:.1f}%"
                                )
                                if reduce_reason:
                                    note_text += f" | 原因: {reduce_reason}"
                                add_psych_note(t["page_id"], note_text)
                                update_trade_status(t["page_id"], {
                                    "Position %": new_position / 100,
                                })
                                st.success(f"减仓成功! 仓位已更新为 {new_position:.1f}%")
                                st.rerun()
                            except Exception as e:
                                st.error(f"减仓失败: {e}")

                    # Tab 4: 更新状态
                    with action_tabs[3]:
                        new_status_options = [s for s in ["PLANNED", "ACTIVE"] if s != t["status"]]
                        if new_status_options:
                            new_status = st.selectbox(
                                "新状态", new_status_options, key=f"status_{idx}")
                            if st.button("更新状态", key=f"update_{idx}"):
                                try:
                                    update_trade_status(t["page_id"], {"Status": new_status})
                                    st.success(f"状态已更新为 {new_status}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"更新失败: {e}")

                    # Tab 5: 添加备注
                    with action_tabs[4]:
                        new_note = st.text_area(
                            "心理备注", placeholder="记录当前心理状态...",
                            key=f"note_{idx}", height=80)
                        if st.button("添加备注", key=f"add_note_{idx}"):
                            if new_note.strip():
                                try:
                                    add_psych_note(t["page_id"], new_note.strip())
                                    st.success("备注已添加")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"添加失败: {e}")
                            else:
                                st.warning("请输入备注内容")
                else:
                    # 已关闭的交易显示结果
                    st.markdown("---")
                    rc1, rc2, rc3 = st.columns(3)
                    rc1.metric("退出价", f"${t['actual_exit']:.2f}" if t["actual_exit"] else "N/A")
                    rc2.metric("R-Multiple", f"{t['r_multiple']:.2f}" if t["r_multiple"] is not None else "N/A")
                    rc3.metric("收益率", f"{t['actual_return_pct']:.2%}" if t["actual_return_pct"] is not None else "N/A")
                    if t["psych_notes"]:
                        st.caption(f"备注: {t['psych_notes']}")

# =====================================================================
# PAGE 3: 月度复盘
# =====================================================================
elif page == "📊 月度复盘":
    st.divider()
    st.markdown("## 月度复盘报告")

    col_y, col_m = st.columns(2)
    with col_y:
        review_year = st.selectbox("年份", list(range(2025, 2028)), index=1)
    with col_m:
        review_month = st.selectbox("月份", list(range(1, 13)),
                                    index=date.today().month - 1,
                                    format_func=lambda m: f"{m}月")

    generate = st.button("生成复盘报告", type="primary", use_container_width=True)

    if generate:
        from analytics_engine import (
            calc_statistics, find_highlights, find_error_fingerprints,
            calc_discipline_score, deep_analysis, generate_suggestions,
            render_html_report, calc_position_analysis, calc_risk_profile,
        )
        from notion_bridge import fetch_all_trades

        _, last_day = calendar.monthrange(review_year, review_month)
        start = f"{review_year}-{review_month:02d}-01T00:00:00Z"
        end = f"{review_year}-{review_month:02d}-{last_day}T23:59:59Z"
        period = f"{review_year}-{review_month:02d}"

        with st.spinner("正在从 Notion 拉取交易记录..."):
            trades = fetch_all_trades(date_range=(start, end))

        if not trades:
            st.warning(f"{period} 无交易记录")
        else:
            stats = calc_statistics(trades)
            highlights = find_highlights(trades)
            fingerprints = find_error_fingerprints(trades)
            discipline = calc_discipline_score(trades)
            deep = deep_analysis(trades)
            position_analysis = calc_position_analysis(trades)
            risk_profile = calc_risk_profile(trades)
            suggestions = generate_suggestions(fingerprints, discipline, risk_profile)

            review_data = {
                "period": period, "trades": trades, "statistics": stats,
                "highlights": highlights, "fingerprints": fingerprints,
                "discipline": discipline, "deep_analysis": deep,
                "suggestions": suggestions, "position_analysis": position_analysis,
                "risk_profile": risk_profile,
            }

            # ── 核心指标卡片 ──
            st.markdown("### 核心指标")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("总交易", stats["total"])
            c2.metric("已关闭", stats.get("closed", 0))
            c3.metric("胜率", f"{stats.get('win_rate', 0):.0%}")
            c4.metric("纪律评分", f"{discipline.get('score', 100):.0f}/100")

            c5, c6, c7, c8 = st.columns(4)
            c5.metric("平均 R", f"{stats.get('avg_r', 0):.2f}")
            c6.metric("最佳 R", f"{stats.get('best_r', 0):.2f}")
            c7.metric("最差 R", f"{stats.get('worst_r', 0):.2f}")
            c8.metric("最大回撤", f"{stats.get('max_drawdown', 0):.2f}R")

            # ── 生成 HTML 并嵌入 ──
            from config import load_config
            cfg = load_config()
            output_dir = cfg.get("reports", {}).get("output_dir", tempfile.gettempdir())
            # 确保目录存在
            try:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
            except OSError:
                output_dir = tempfile.gettempdir()
            output_path = f"{output_dir}/{period}_review.html"
            render_html_report(review_data, output_path)

            with open(output_path, "r") as f:
                html_content = f.read()
            st.markdown("### 交互式图表")
            st.components.v1.html(html_content, height=2100, scrolling=True)

            # ── 仓位分布与个股收益 ──
            st.markdown("### 仓位分布与个股收益")

            # 仓位概览
            pos_dist = position_analysis.get("position_dist", [])
            total_pos = position_analysis.get("total_position", 0)
            max_conc = position_analysis.get("max_concentration", 0)
            pc1, pc2, pc3 = st.columns(3)
            pc1.metric("总仓位", f"{total_pos:.1f}%")
            pc2.metric("持仓标的数", len(pos_dist))
            pc3.metric("最大集中度", f"{max_conc:.0f}%")

            if pos_dist:
                for p in pos_dist:
                    st.markdown(f"**{p['ticker']}** ({p['direction']}) — {p['position_pct']:.1f}% | {p['status']}")

            st.markdown("---")

            # 个股收益
            ticker_stats = position_analysis.get("ticker_stats", {})
            if ticker_stats:
                for ticker, ts in ticker_stats.items():
                    wr_color = "green" if ts["win_rate"] >= 0.5 else "red"
                    r_color = "green" if ts["total_r"] >= 0 else "red"
                    st.markdown(
                        f"**{ticker}** — "
                        f"交易 {ts['trades']} 笔 | "
                        f"胜率 :{wr_color}[{ts['win_rate']:.0%}] | "
                        f"平均R :{r_color}[{ts['avg_r']:.2f}] | "
                        f"总R :{r_color}[{ts['total_r']:.2f}] | "
                        f"平均收益 {ts['avg_return']:.2%}"
                    )
            else:
                st.caption("暂无已关闭交易的个股数据")

            total_wr = position_analysis.get("total_weighted_return", 0)
            st.metric("账户加权总收益", f"{total_wr:.2%}")

            # ── 风险偏好分析 ──
            st.markdown("### 风险偏好分析")
            rp_score = risk_profile.get("score", 50)
            rp_label = risk_profile.get("label", "数据不足")

            rp1, rp2 = st.columns([1, 2])
            with rp1:
                st.metric("风险偏好评分", f"{rp_score:.0f}/100")
                st.markdown(f"**类型: {rp_label}**")
            with rp2:
                for f in risk_profile.get("factors", []):
                    bar_pct = f["score"]
                    bar_color = "#FF1744" if bar_pct >= 70 else "#FFC107" if bar_pct >= 40 else "#00C853"
                    st.markdown(
                        f"**{f['name']}**: {f['value']} ({f['detail']}) — "
                        f"激进度 {bar_pct:.0f}/100"
                    )
                    st.progress(min(bar_pct / 100, 1.0))

            # ── 高光时刻 ──
            if highlights:
                st.markdown("### 高光时刻")
                for h in highlights:
                    st.success(f"**{h['ticker']}** {h['r_multiple']:.2f}R | {h.get('entry_emotion', '')} | {h.get('thesis', '')[:80]}")

            # ── 错误指纹 ──
            if fingerprints.get("patterns"):
                st.markdown("### 错误指纹")
                for p in fingerprints["patterns"]:
                    st.error(p)

            # ── 深度分析 ──
            if deep.get("insights"):
                st.markdown("### 深度分析")
                for insight in deep["insights"]:
                    st.warning(insight)

            # ── 行动建议 ──
            st.markdown("### 行动建议")
            for s in suggestions:
                st.info(s)

            # ── 同步到 Notion ──
            st.divider()
            sync_notion = st.button("同步报告摘要到 Notion", use_container_width=True)
            if sync_notion:
                try:
                    from notion_bridge import ensure_database
                    client, db_id = ensure_database()
                    summary_text = (
                        f"月度复盘 {period}\n"
                        f"总交易: {stats['total']} | 已关闭: {stats.get('closed', 0)}\n"
                        f"胜率: {stats.get('win_rate', 0):.0%} | 平均R: {stats.get('avg_r', 0):.2f}\n"
                        f"纪律评分: {discipline.get('score', 100):.0f}/100\n\n"
                        f"行动建议:\n" + "\n".join(f"• {s}" for s in suggestions)
                    )
                    parent_page_id = cfg.get("notion", {}).get("parent_page_id", "")
                    client.pages.create(
                        parent={"type": "page_id", "page_id": parent_page_id},
                        properties={"title": [{"text": {"content": f"Review {period}"}}]},
                        children=[
                            {"object": "block", "type": "heading_2",
                             "heading_2": {"rich_text": [{"text": {"content": f"月度复盘 — {period}"}}]}},
                            {"object": "block", "type": "paragraph",
                             "paragraph": {"rich_text": [{"text": {"content": summary_text}}]}},
                        ],
                    )
                    st.success("报告摘要已同步到 Notion!")
                except Exception as e:
                    st.error(f"Notion 同步失败: {e}")

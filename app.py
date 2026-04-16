import streamlit as st
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from data_engine      import get_all_data
from indicator_engine import calculate_indicators, get_signals, calculate_score
from market_engine    import (get_market_conditions, get_sector_data,
                               get_macro_calendar, get_best_time_to_trade)
from options_engine   import (get_best_option, get_most_active_expiry,
                               get_alternative_strategy, get_options_flow,
                               calculate_max_pain, get_put_call_ratio)
from risk_engine      import (calculate_targets, calculate_position_size,
                               calculate_drawdown, calculate_expected_value,
                               calculate_swing_score)
from ai_engine        import get_ai_analysis
from tracker          import (get_stats, get_open_trades, log_trade,
                               close_trade, get_rules_for_prompt,
                               get_confidence_adjustment)

st.set_page_config(
    page_title="AI Stock Analyzer",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
.big-signal-buy  { font-size:32px; font-weight:700; color:#22c55e; }
.big-signal-sell { font-size:32px; font-weight:700; color:#ef4444; }
.big-signal-hold { font-size:32px; font-weight:700; color:#f59e0b; }
.metric-label    { font-size:12px; color:#888; margin-bottom:2px; }
.metric-val      { font-size:20px; font-weight:600; }
.green  { color:#22c55e; }
.red    { color:#ef4444; }
.amber  { color:#f59e0b; }
.veteran-box {
    background:#052e16; border:1px solid #166534;
    border-radius:12px; padding:20px; margin:10px 0;
    color:#bbf7d0; font-style:italic; line-height:1.8;
}
.warning-box {
    background:#431407; border:1px solid #9a3412;
    border-radius:8px; padding:12px; margin:8px 0; color:#fed7aa;
}
.score-bar-wrap { background:#1e293b; border-radius:4px; height:8px; margin:4px 0; }
.stTabs [data-baseweb="tab-list"] { gap:8px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    st.markdown("## 📈 AI Stock Analyzer")
    st.caption("Professional trading analysis powered by Claude AI")
with col2:
    stats = get_stats()
    if stats['total_trades'] > 0:
        st.metric("Your Win Rate", f"{stats['win_rate']}%")
with col3:
    if stats['total_trades'] > 0:
        pnl_color = "normal" if stats['total_pnl'] >= 0 else "inverse"
        st.metric("Total PnL", f"${stats['total_pnl']}")

st.divider()

# ── Input Row ─────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
with col1:
    ticker = st.text_input("Stock Ticker", value="AAPL",
                            placeholder="AAPL, TSLA, NVDA...").upper().strip()
with col2:
    interval = st.selectbox("Timeframe",
                             ["1m","5m","15m","1h","4h","1d"],
                             index=3)
with col3:
    account_size = st.number_input("Account Size ($)",
                                    value=10000, step=1000, min_value=1000)
with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🔍 Analyze", type="primary", use_container_width=True)

# ── Main Analysis ─────────────────────────────────────────────
if analyze_btn and ticker:
    with st.spinner(f"Fetching live data for {ticker}..."):
        data = get_all_data(ticker, interval)

    if data['df'] is None:
        st.error(f"Could not fetch data for {ticker}. Check the ticker symbol.")
        st.stop()

    with st.spinner("Calculating indicators..."):
        df      = calculate_indicators(data['df'])
        signals = get_signals(df)
        signal, confidence, bull, bear = calculate_score(signals)

    with st.spinner("Fetching market data..."):
        market = get_market_conditions()
        sector = get_sector_data(ticker)
        timing = get_best_time_to_trade()
        macro  = get_macro_calendar()

    with st.spinner("Analyzing options chain..."):
        expiry   = get_most_active_expiry(data['options']) if data['options'] else None
        best_opt = get_best_option(data['options'], signals['close'], signal, expiry) if data['options'] else None
        alt_strat= get_alternative_strategy(best_opt, data['options'], signal, signals['close']) if data['options'] else None
        flow     = get_options_flow(data['options'], expiry) if data['options'] and expiry else {}
        max_pain = calculate_max_pain(data['options'], expiry) if data['options'] and expiry else None
        pc_ratio = get_put_call_ratio(data['options'], expiry) if data['options'] and expiry else None

    with st.spinner("Calculating risk & targets..."):
        targets  = calculate_targets(signals['close'], signal, signals['atr'], signals)
        sizing   = calculate_position_size(account_size, 2,
                                            best_opt['premium'] if best_opt else 1)
        drawdown = calculate_drawdown(sizing.get('recommended', 1),
                                       account_size,
                                       best_opt['premium'] if best_opt else 1)
        ev       = calculate_expected_value(75,
                                             sizing.get('contract_cost', 300) * 2,
                                             sizing.get('contract_cost', 300))
        swing    = calculate_swing_score(signals, market, sector,
                                          data['options'], best_opt,
                                          data['earnings'], timing)

    conf_adj, adj_rules = get_confidence_adjustment(ticker,
                                                     signals.get('setup_tags', []))
    adjusted_conf = min(99, max(1, confidence + conf_adj))

    # ── Earnings Warning ──────────────────────────────────────
    if data['earnings'].get('warning'):
        st.markdown(f"""<div class="warning-box">
        ⚠️ <b>EARNINGS WARNING</b> — {data['earnings'].get('earnings_date')}
        ({data['earnings'].get('days_until')} days away) |
        IV crush risk VERY HIGH — close positions before earnings
        </div>""", unsafe_allow_html=True)

    # ── Timing Warning ────────────────────────────────────────
    if timing.get('window') in ['AVOID', 'RISKY']:
        st.markdown(f"""<div class="warning-box">
        🕐 <b>TIMING:</b> {timing.get('window')} —
        {timing.get('reason')} | Current time: {timing.get('current_time')}
        </div>""", unsafe_allow_html=True)

    # ── Top Metrics ───────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Live Price",   f"${signals['close']}")
    with c2:
        delta_color = "normal" if "BUY" in signal else "inverse"
        st.metric("Signal",       signal,
                   delta=f"{adjusted_conf}% confidence")
    with c3:
        pre = data['premarket']
        st.metric("Pre-Market",
                   f"${pre.get('pre_market_price', 'N/A')}",
                   delta=f"{pre.get('gap_direction','')} {pre.get('gap_pct',0)}%")
    with c4:
        st.metric("Swing Score",  f"{swing['score']}/10",
                   delta=swing['verdict'])
    with c5:
        target = data['analyst'].get('target_mean', None)
        try:
            target_display = f"${round(float(target), 2)}" if target else "N/A"
        except:
            target_display = "N/A"
        rec = (data['analyst'].get('recommendation') or '').upper()
        st.metric("Analyst Target",
           target_display,
           delta=rec if rec else None)

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────
    tabs = st.tabs(["📊 Chart & Targets", "📅 Options",
                    "🌍 Market", "💼 Risk", "🏆 Verdict", "📋 Tracker"])

    # ── Tab 1: Chart ──────────────────────────────────────────
    with tabs[0]:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Chart Analysis")
            data_rows = [
                ("Entry zone",   f"${targets.get('entry_low')} — ${targets.get('entry_high')}", ""),
                ("Don't chase",  f"Above ${targets.get('dont_chase')}", "amber"),
                ("Stop loss",    f"${targets.get('stop_loss')}", "red"),
                ("TP1",          f"${targets.get('tp1')}", "green"),
                ("TP2",          f"${targets.get('tp2')}", "green"),
                ("TP3 (max)",    f"${targets.get('tp3')}", "green"),
                ("Risk/Reward",  f"1:{targets.get('rr_ratio')}", "green"),
                ("Support",      f"${signals.get('support')}", ""),
                ("Resistance",   f"${signals.get('resistance')}", ""),
                ("VWAP",         f"${signals.get('vwap')}", ""),
            ]
            for label, value, color in data_rows:
                c1, c2 = st.columns([1, 1])
                c1.markdown(f"<span style='color:#888;font-size:13px'>{label}</span>",
                             unsafe_allow_html=True)
                c2.markdown(f"<span class='{color}' style='font-size:13px;font-weight:600'>{value}</span>",
                             unsafe_allow_html=True)
            st.divider()
            st.caption(f"Hold period: ~{targets.get('hold_days')} days")

        with col2:
            st.subheader("Indicators")
            ind_rows = [
                ("RSI (14)",       signals.get('rsi'),
                 "green" if signals.get('rsi_bullish') else "red"),
                ("ADX",            signals.get('adx'),
                 "green" if signals.get('strong_trend') else "amber"),
                ("Vol ratio",      f"{signals.get('vol_ratio')}x",
                 "green" if signals.get('high_volume') else "amber"),
                ("Above EMA 200",  "✅ Yes" if signals.get('above_ema200') else "❌ No",
                 "green" if signals.get('above_ema200') else "red"),
                ("EMA stack bull", "✅ Yes" if signals.get('ema_bullish') else "❌ No",
                 "green" if signals.get('ema_bullish') else "red"),
                ("MACD bullish",   "✅ Yes" if signals.get('macd_bullish') else "❌ No",
                 "green" if signals.get('macd_bullish') else "red"),
                ("MACD cross",     "✅ Yes" if signals.get('macd_cross') else "No",
                 "green" if signals.get('macd_cross') else ""),
                ("Above VWAP",     "✅ Yes" if signals.get('above_vwap') else "❌ No",
                 "green" if signals.get('above_vwap') else "red"),
                ("Bull engulf",    "✅ Yes" if signals.get('bull_engulf') else "No",
                 "green" if signals.get('bull_engulf') else ""),
                ("Pin bar bull",   "✅ Yes" if signals.get('pin_bar_bull') else "No",
                 "green" if signals.get('pin_bar_bull') else ""),
            ]
            for label, value, color in ind_rows:
                c1, c2 = st.columns([1, 1])
                c1.markdown(f"<span style='color:#888;font-size:13px'>{label}</span>",
                             unsafe_allow_html=True)
                c2.markdown(f"<span class='{color}' style='font-size:13px;font-weight:600'>{value}</span>",
                             unsafe_allow_html=True)

    # ── Tab 2: Options ────────────────────────────────────────
    with tabs[1]:
        if best_opt:

            # ── Top 5 Options Table ───────────────────────────
            st.subheader("🏆 Top 5 Best Options — Ranked by Volume & Score")

            from options_engine import get_best_options
            top_options = get_best_options(
                data['options'], signals['close'], signal, expiry, top_n=5)

            if top_options:
                for opt in top_options:
                    score     = opt['score']
                    score_color = ("🟢" if score >= 70 else
                                   "🟡" if score >= 50 else "🔴")
                    with st.expander(
                        f"#{opt['rank']} {score_color} "
                        f"{opt['type']} ${opt['strike']} | "
                        f"Premium ${opt['premium']} | "
                        f"Vol {opt['volume']:,} | "
                        f"Score {opt['score']}/100",
                        expanded = opt['rank'] == 1
                    ):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Strike",       f"${opt['strike']}")
                        c2.metric("Premium",      f"${opt['premium']}")
                        c3.metric("Contract cost",f"${opt['contract_cost']}")
                        c4.metric("Expiry",       opt['expiry'])

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Delta",        opt['delta'])
                        c2.metric("Theta/day",    f"${opt['theta']}")
                        c3.metric("IV",           f"{opt['iv']}%")
                        c4.metric("Prob ITM",     f"{opt['prob_itm']}%")

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Volume",       f"{opt['volume']:,}")
                        c2.metric("Open Interest",f"{opt['open_interest']:,}")
                        c3.metric("Break even",   f"${opt['break_even']}")
                        c4.metric("Theta burn",   f"${opt['total_theta_burn']}")

                        # Recommendation tag
                        if opt['delta'] >= 0.4 and opt['volume'] > 1000:
                            st.success("✅ High conviction — good delta & volume")
                        elif opt['iv'] > 40:
                            st.warning("⚠️ IV elevated — consider spread instead")
                        elif opt['prob_itm'] < 20:
                            st.error("❌ Low prob ITM — needs large move to profit")
                        else:
                            st.info("ℹ️ Moderate setup — check market conditions")

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Best Option Detail")
                opt_rows = [
                    ("Action",        f"BUY {best_opt.get('type')}", "green"),
                    ("Strike",        f"${best_opt.get('strike')}", ""),
                    ("Expiry",        best_opt.get('expiry'), ""),
                    ("Premium",       f"${best_opt.get('premium')}", ""),
                    ("Contract cost", f"${best_opt.get('contract_cost')}", ""),
                    ("IV",            f"{best_opt.get('iv')}%",
                     "red" if best_opt.get('iv', 0) > 40 else "amber"),
                    ("Delta",         best_opt.get('delta'), ""),
                    ("Theta/day",     f"${best_opt.get('theta')}", "red"),
                    ("Break even",    f"${best_opt.get('break_even')}", "amber"),
                    ("Prob ITM",      f"{best_opt.get('prob_itm')}%", ""),
                ]
                for label, value, color in opt_rows:
                    c1, c2 = st.columns([1, 1])
                    c1.markdown(
                        f"<span style='color:#888;font-size:13px'>{label}</span>",
                        unsafe_allow_html=True)
                    c2.markdown(
                        f"<span class='{color}' style='font-size:13px;"
                        f"font-weight:600'>{value}</span>",
                        unsafe_allow_html=True)

            with col2:
                st.subheader("Options Flow")
                if flow:
                    flow_rows = [
                        ("Most active expiry",  expiry, ""),
                        ("Put/Call ratio",       pc_ratio,
                         "green" if pc_ratio and pc_ratio < 0.8 else "red"),
                        ("Max pain",             f"${max_pain}", ""),
                        ("Top call strike",      f"${flow.get('top_call_strike')}", "green"),
                        ("Top call volume",      f"{flow.get('top_call_volume'):,}", ""),
                        ("Highest OI strike",    f"${flow.get('highest_oi_strike')}", ""),
                        ("Highest OI",           f"{flow.get('highest_oi'):,}", ""),
                    ]
                    for label, value, color in flow_rows:
                        c1, c2 = st.columns([1, 1])
                        c1.markdown(
                            f"<span style='color:#888;font-size:13px'>{label}</span>",
                            unsafe_allow_html=True)
                        c2.markdown(
                            f"<span class='{color}' style='font-size:13px;"
                            f"font-weight:600'>{value}</span>",
                            unsafe_allow_html=True)

                    if flow.get('unusual_activity'):
                        st.markdown("**Unusual activity:**")
                        for ua in flow['unusual_activity']:
                            st.markdown(f"🔥 {ua}")

            if alt_strat:
                st.divider()
                st.subheader("💡 Smarter Alternative")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Strategy",   alt_strat.get('strategy'))
                c2.metric("Net cost",   f"${alt_strat.get('net_cost')}")
                c3.metric("Max profit", f"${alt_strat.get('max_profit')}")
                c4.metric("You save",   f"${alt_strat.get('savings')}")
                st.info(f"💡 {alt_strat.get('reason')}")
        else:
            st.info("No options data available for this ticker")

    # ── Tab 3: Market ─────────────────────────────────────────
    with tabs[2]:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("Market Conditions")
            st.metric("S&P 500",      f"${market.get('spy_price')}",
                       delta=market.get('spy_trend'))
            st.metric("VIX",          market.get('vix'),
                       delta=market.get('vix_status'))
            st.metric("Market mood",  market.get('market_mood'))

        with col2:
            st.subheader("Sector")
            st.metric("Sector",       sector.get('sector'))
            st.metric("Trend",        sector.get('sector_trend'))
            st.metric("1 week chg",   f"{sector.get('sector_1w_chg')}%")
            st.metric("Hot sector",   sector.get('hot_sector'))

        with col3:
            st.subheader("Trade Timing")
            window = timing.get('window')
            color  = ("🟢" if window == 'BEST'    else
                      "🟡" if window == 'GOOD'    else
                      "🔴")
            st.markdown(f"### {color} {window}")
            st.markdown(f"*{timing.get('reason')}*")
            st.caption(f"Current time: {timing.get('current_time')}")

        st.divider()
        st.subheader("📅 Macro Calendar")
        events = macro.get('events', [])
        for event in events:
            icon = "🚨" if event['impact'] == 'VERY HIGH' else "⚠️" if event['impact'] == 'HIGH' else "📌"
            st.markdown(f"{icon} **{event['date']}** — {event['event']} | Impact: {event['impact']}")

    # ── Tab 4: Risk ───────────────────────────────────────────
    with tabs[3]:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Position Sizing")
            st.metric("Account size",    f"${account_size:,}")
            st.metric("Max risk (2%)",   f"${sizing.get('max_risk')}")
            st.metric("Contract cost",   f"${sizing.get('contract_cost')}")
            st.metric("Recommended",     f"{sizing.get('recommended')} contract(s)",
                       delta="Safe size" if sizing.get('safe') else "Over-sized")
            st.metric("Actual risk",     f"${sizing.get('actual_risk')}")

            st.divider()
            st.subheader("Expected Value")
            ev_val = ev.get('expected_value', 0)
            st.metric("Expected value per trade",
                       f"${ev_val}",
                       delta="Positive EV ✅" if ev_val > 0 else "Negative EV ❌")
            st.metric("Win rate assumed", f"{ev.get('win_rate')}%")

        with col2:
            st.subheader("Drawdown Simulator")
            st.markdown("*What happens if this trade goes wrong:*")
            st.metric("Total invested",     f"${drawdown.get('total_invested')}")
            st.metric("If down 50%",        f"-${drawdown.get('loss_50pct')}",
                       delta=f"-{drawdown.get('impact_50')}% of account")
            st.metric("Full loss",          f"-${drawdown.get('loss_full')}",
                       delta=f"-{drawdown.get('impact_full')}% of account")
            st.metric("3 losses in a row",  f"-${drawdown.get('loss_3x_streak')}",
                       delta=f"-{drawdown.get('impact_3x_streak')}% of account")

            safe = drawdown.get('account_safe')
            if safe:
                st.success("✅ Account is safe — position size is appropriate")
            else:
                st.error("⚠️ Risk is high — consider reducing position size")

        if adj_rules:
            st.divider()
            st.subheader("🧠 Personal Learned Adjustments")
            for rule in adj_rules:
                st.markdown(f"• {rule}")
            st.metric("Confidence adjustment",
                       f"{'+' if conf_adj >= 0 else ''}{conf_adj}%",
                       delta=f"Adjusted confidence: {adjusted_conf}%")

    # ── Tab 5: Verdict ────────────────────────────────────────
    with tabs[4]:
        st.subheader("🏆 Veteran Trader Verdict")

        with st.spinner("Claude AI is analyzing all data like a 20-year veteran trader..."):
            rules_context = get_rules_for_prompt()
            analysis = get_ai_analysis(
                ticker, interval, signals, signal, adjusted_conf,
                targets, sizing, drawdown, ev, swing,
                market, sector, timing, macro,
                data['options'], best_opt, alt_strat,
                data['analyst'], data['premarket'], data['earnings']
            )

        st.markdown(f'<div class="veteran-box">{analysis}</div>',
                     unsafe_allow_html=True)

        st.divider()
        st.subheader("📊 Scorecard")
        score_items = [
            ("Technical setup",    bull / 15 * 10),
            ("Options flow",       7 if best_opt else 3),
            ("Market conditions",  8 if market.get('good_for_calls') else 6),
            ("Risk/Reward",        min(10, targets.get('rr_ratio', 1) * 3)),
            ("Liquidity",          9 if best_opt and best_opt.get('open_interest', 0) > 1000 else 5),
            ("Overall",            swing['score']),
        ]
        for label, score in score_items:
            score = round(min(10, max(0, score)), 1)
            c1, c2, c3 = st.columns([2, 6, 1])
            c1.markdown(f"<span style='font-size:13px;color:#888'>{label}</span>",
                         unsafe_allow_html=True)
            c2.progress(score / 10)
            c3.markdown(f"**{score}**")

    # ── Tab 6: Tracker ────────────────────────────────────────
    with tabs[5]:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📋 Log This Trade")
            with st.form("log_trade_form"):
                log_notes = st.text_area("Notes / why you're taking this trade", height=80)
                setup_tags_input = st.multiselect(
                    "Setup tags",
                    ["ema_cross", "high_volume", "low_volume", "earnings_risk",
                     "gap_up", "gap_down", "oversold", "overbought",
                     "breakout", "pullback", "vwap_bounce"]
                )
                submitted = st.form_submit_button("📝 Log Trade", type="primary")
                if submitted and best_opt:
                    trade_id = log_trade(
                        ticker      = ticker,
                        signal      = signal,
                        entry_price = signals['close'],
                        strike      = best_opt.get('strike'),
                        expiry      = best_opt.get('expiry'),
                        premium     = best_opt.get('premium'),
                        contracts   = sizing.get('recommended', 1),
                        stop_loss   = targets.get('stop_loss'),
                        tp1         = targets.get('tp1'),
                        tp2         = targets.get('tp2'),
                        tp3         = targets.get('tp3'),
                        swing_score = swing['score'],
                        confidence  = adjusted_conf,
                        setup_tags  = setup_tags_input,
                        notes       = log_notes
                    )
                    st.success(f"✅ Trade #{trade_id} logged!")

        with col2:
            st.subheader("📊 Your Stats")
            if stats['total_trades'] > 0:
                c1, c2 = st.columns(2)
                c1.metric("Total trades",   stats['total_trades'])
                c2.metric("Win rate",       f"{stats['win_rate']}%")
                c1.metric("Total PnL",      f"${stats['total_pnl']}")
                c2.metric("Profit factor",  stats['profit_factor'])
                c1.metric("Avg win",        f"${stats['avg_win']}")
                c2.metric("Avg loss",       f"${stats['avg_loss']}")
                c1.metric("Learned rules",  stats.get('learned_rules', 0))
            else:
                st.info("No trades logged yet. Start logging trades to build your stats!")

        open_trades = get_open_trades()
        if open_trades:
            st.divider()
            st.subheader("Open Trades")
            for trade in open_trades:
                with st.expander(f"#{trade['id']} {trade['ticker']} {trade['signal']} — opened {trade['date']}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Entry",    f"${trade['entry_price']}")
                    c2.metric("Premium",  f"${trade['premium']}")
                    c3.metric("Cost",     f"${trade['cost']}")

                    with st.form(f"close_{trade['id']}"):
                        exit_price   = st.number_input("Exit stock price", value=float(trade['entry_price']))
                        exit_premium = st.number_input("Exit option premium", value=float(trade['premium']))
                        result       = st.selectbox("Result", ["WIN", "LOSS", "BREAKEVEN"])
                        feedback     = st.text_input("What happened?")
                        what_wrong   = st.text_area("What went wrong / what you learned", height=60)
                        if st.form_submit_button("Close Trade"):
                            pnl = close_trade(trade['id'], exit_price,
                                               exit_premium, result,
                                               feedback, what_wrong)
                            st.success(f"Trade closed! PnL: ${pnl}")
                            st.rerun()
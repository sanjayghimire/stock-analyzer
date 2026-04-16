import anthropic
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)


def build_prompt(ticker, interval, signals, signal, confidence,
                 targets, sizing, drawdown, ev, swing,
                 market, sector, timing, macro,
                 options_data, best_option, alt_strategy,
                 analyst, premarket, earnings):

    earnings_warning = ""
    if earnings.get('warning'):
        earnings_warning = f"""
EARNINGS WARNING: Earnings in {earnings.get('days_until')} days ({earnings.get('earnings_date')})
IV crush risk is VERY HIGH after earnings. Factor this into your recommendation."""

    options_section = ""
    if best_option:
        options_section = f"""
OPTIONS DATA:
- Best option: ${best_option.get('strike')} {best_option.get('type')} | Expiry: {best_option.get('expiry')}
- Premium: ${best_option.get('premium')} (${best_option.get('contract_cost')}/contract)
- IV: {best_option.get('iv')}% | Delta: {best_option.get('delta')} | Theta: {best_option.get('theta')}/day
- Break even: ${best_option.get('break_even')} | Prob ITM: {best_option.get('prob_itm')}%
- Open interest: {best_option.get('open_interest')} | Volume: {best_option.get('volume')}"""

    alt_section = ""
    if alt_strategy:
        alt_section = f"""
ALTERNATIVE STRATEGY:
- {alt_strategy.get('strategy')}: Buy {alt_strategy.get('buy')} / Sell {alt_strategy.get('sell')}
- Net cost: ${alt_strategy.get('net_cost')} | Max profit: ${alt_strategy.get('max_profit')}
- Reason: {alt_strategy.get('reason')}"""

    prompt = f"""You are a veteran stock and options trader with 20+ years of experience.
You have traded through multiple market cycles and know how to read confluence of signals.
You are analyzing {ticker} on the {interval} timeframe.
Give your FINAL VERDICT like a seasoned professional who has seen everything.
Be direct, specific, and actionable. No fluff.

{earnings_warning}

=== TECHNICAL ANALYSIS ===
Signal: {signal} | Confidence: {confidence}%
Price: ${signals.get('close')} | VWAP: ${signals.get('vwap')}
RSI: {signals.get('rsi')} | ADX: {signals.get('adx')} | Vol ratio: {signals.get('vol_ratio')}x
Above EMA9: {signals.get('above_ema9')} | EMA21: {signals.get('above_ema21')} | EMA50: {signals.get('above_ema50')} | EMA200: {signals.get('above_ema200')}
MACD Bullish: {signals.get('macd_bullish')} | MACD Cross: {signals.get('macd_cross')}
Bull Engulf: {signals.get('bull_engulf')} | Pin Bar Bull: {signals.get('pin_bar_bull')}
Support: ${signals.get('support')} | Resistance: ${signals.get('resistance')}

=== PRICE TARGETS ===
Entry zone: ${targets.get('entry_low')} - ${targets.get('entry_high')}
Don't chase above: ${targets.get('dont_chase')}
Stop loss: ${targets.get('stop_loss')}
TP1: ${targets.get('tp1')} | TP2: ${targets.get('tp2')} | TP3: ${targets.get('tp3')}
Risk/Reward: 1:{targets.get('rr_ratio')} | Hold: {targets.get('hold_days')} days

=== OPTIONS ===
{options_section}
{alt_section}

=== MARKET CONDITIONS ===
S&P 500: {market.get('spy_trend')} | VIX: {market.get('vix')} ({market.get('vix_status')})
Market mood: {market.get('market_mood')}
Sector ({sector.get('sector')}): {sector.get('sector_trend')} | 1W: {sector.get('sector_1w_chg')}%
Trade window: {timing.get('window')} - {timing.get('reason')}

=== ANALYST & FUNDAMENTALS ===
Wall St consensus: {analyst.get('recommendation')} | Analysts: {analyst.get('num_analysts')}
Avg target: ${analyst.get('target_mean')} | High: ${analyst.get('target_high')}

=== PRE-MARKET ===
Pre-market price: {premarket.get('pre_market_price')} | Gap: {premarket.get('gap_direction')} {premarket.get('gap_pct')}%

=== RISK ANALYSIS ===
Position size: {sizing.get('recommended')} contract(s) | Cost: ${sizing.get('actual_risk')}
Max loss: ${drawdown.get('loss_full')} ({drawdown.get('impact_full')}% of account)
Expected value: ${ev.get('expected_value')} | Win rate assumed: {ev.get('win_rate')}%
Swing score: {swing.get('score')}/10 - {swing.get('verdict')}

=== YOUR TASK ===
Provide your FINAL VETERAN TRADER VERDICT in this EXACT format:

OVERALL BIAS: [STRONGLY BULLISH/BULLISH/NEUTRAL/BEARISH/STRONGLY BEARISH]
CONVICTION: [X.X/10]

THE PLAY:
- Action: [BUY CALL / BUY PUT / BUY CALL SPREAD / AVOID]
- Strike: $[X]
- Expiry: [date]
- Max pay: $[X] premium ($[X]/contract)

EXECUTION PLAN:
- When to enter: [specific condition]
- Entry price: $[X] - $[X]
- Stop loss: $[X] (reason)
- Option stop: Exit if premium drops to $[X]

PROFIT TARGETS:
- TP1: $[X] - Take 30% off table
- TP2: $[X] - Take 40% off table
- TP3: $[X] - Let 30% ride
- Max upside: $[X]

RISK WARNINGS:
[List all real risks - earnings, IV, macro, timing]

TRADE MANAGEMENT RULES:
[5 specific rules for managing this exact trade]

SCORECARD:
- Technical: [X/10]
- Options flow: [X/10]
- Market conditions: [X/10]
- Risk/Reward: [X/10]
- News/Catalyst: [X/10]
- Liquidity: [X/10]
- OVERALL: [X/10]

FINAL CALL: [TAKE THE TRADE / WAIT FOR BETTER SETUP / AVOID]

VETERAN NOTES:
[2-3 sentences of hard-earned wisdom specific to THIS setup right now.]"""

    return prompt


def get_ai_analysis(ticker, interval, signals, signal, confidence,
                    targets, sizing, drawdown, ev, swing,
                    market, sector, timing, macro,
                    options_data, best_option, alt_strategy,
                    analyst, premarket, earnings):
    try:
        prompt = build_prompt(
            ticker, interval, signals, signal, confidence,
            targets, sizing, drawdown, ev, swing,
            market, sector, timing, macro,
            options_data, best_option, alt_strategy,
            analyst, premarket, earnings
        )

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    except Exception as e:
        return f"AI analysis error: {e}"


if __name__ == "__main__":
    from data_engine      import get_all_data
    from indicator_engine import calculate_indicators, get_signals, calculate_score
    from market_engine    import (get_market_conditions, get_sector_data,
                                   get_macro_calendar, get_best_time_to_trade)
    from options_engine   import (get_best_option, get_most_active_expiry,
                                   get_alternative_strategy)
    from risk_engine      import (calculate_targets, calculate_position_size,
                                   calculate_drawdown, calculate_expected_value,
                                   calculate_swing_score)

    print("Running full AI analysis on AAPL...")
    ticker   = "AAPL"
    interval = "1h"

    data     = get_all_data(ticker, interval)
    df       = calculate_indicators(data['df'])
    signals  = get_signals(df)
    signal, confidence, _, _ = calculate_score(signals)

    market   = get_market_conditions()
    sector   = get_sector_data(ticker)
    timing   = get_best_time_to_trade()
    macro    = get_macro_calendar()

    expiry   = get_most_active_expiry(data['options'])
    best_opt = get_best_option(data['options'], signals['close'], signal, expiry)
    alt_strat= get_alternative_strategy(
        best_opt, data['options'], signal, signals['close'])

    targets  = calculate_targets(signals['close'], signal, signals['atr'], signals)
    sizing   = calculate_position_size(
        10000, 2, best_opt['premium'] if best_opt else 1)
    drawdown = calculate_drawdown(
        sizing.get('recommended', 1), 10000,
        best_opt['premium'] if best_opt else 1)
    ev       = calculate_expected_value(
        75, sizing.get('contract_cost', 300) * 2,
        sizing.get('contract_cost', 300))
    swing    = calculate_swing_score(
        signals, market, sector, data['options'],
        best_opt, data['earnings'], timing)

    print("Sending to Claude AI for veteran analysis...\n")
    analysis = get_ai_analysis(
        ticker, interval, signals, signal, confidence,
        targets, sizing, drawdown, ev, swing,
        market, sector, timing, macro,
        data['options'], best_opt, alt_strat,
        data['analyst'], data['premarket'], data['earnings']
    )

    print(analysis)
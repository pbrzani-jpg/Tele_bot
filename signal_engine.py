# signal_engine.py

import ta
import pandas as pd

def get_signal(df: pd.DataFrame) -> str:
    close = df['close']

    df['rsi'] = ta.momentum.RSIIndicator(close, window=14).rsi()
    df['ema'] = ta.trend.EMAIndicator(close, window=14).ema_indicator()

    macd = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()

    latest = df.iloc[-1]

    rsi = latest['rsi']
    price = latest['close']
    ema = latest['ema']
    macd_diff = latest['macd_diff']

    buy_signals = 0
    sell_signals = 0

    if rsi < 30:
        buy_signals += 1
    elif rsi > 70:
        sell_signals += 1

    if price > ema:
        buy_signals += 1
    elif price < ema:
        sell_signals += 1

    if macd_diff > 0:
        buy_signals += 1
    elif macd_diff < 0:
        sell_signals += 1

    rsi_bar = _progress_bar(rsi, 0, 100)
    macd_arrow = "↑" if macd_diff > 0 else "↓"

    details = (
        f"\n📊 *تفاصيل المؤشرات:*\n"
        f"• RSI: `{rsi:.1f}` {rsi_bar}\n"
        f"• EMA: `{ema:.3f}` {'✅ فوقه' if price > ema else '❌ تحته'}\n"
        f"• MACD: `{macd_diff:.5f}` {macd_arrow}\n"
        f"• قوة الإشارة: {buy_signals if buy_signals > sell_signals else sell_signals}/3 مؤشرات"
    )

    if buy_signals == 3:
        return f"🔼 *إشارة شراء قوية* ✅✅✅{details}"
    elif buy_signals == 2:
        return f"🔼 *إشارة شراء* ✅✅{details}"
    elif sell_signals == 3:
        return f"🔽 *إشارة بيع قوية* ✅✅✅{details}"
    elif sell_signals == 2:
        return f"🔽 *إشارة بيع* ✅✅{details}"
    else:
        return f"⚠️ *لا توجد إشارة واضحة*{details}"

def _progress_bar(value, min_val, max_val, length=5):
    filled = int((value - min_val) / (max_val - min_val) * length)
    filled = max(0, min(length, filled))
    return "█" * filled + "░" * (length - filled)

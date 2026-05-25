# signal_engine.py

import ta
import pandas as pd
import numpy as np

def get_signal(df: pd.DataFrame) -> str:
    close = df['close']
    high = df['high']
    low = df['low']

    # === RSI ===
    df['rsi'] = ta.momentum.RSIIndicator(close, window=14).rsi()

    # === EMA (fast + slow) ===
    df['ema_fast'] = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    df['ema_slow'] = ta.trend.EMAIndicator(close, window=21).ema_indicator()

    # === MACD ===
    macd = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()

    # === Bollinger Bands ===
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_mid'] = bb.bollinger_mavg()

    # === Stochastic ===
    stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()

    # === CCI ===
    df['cci'] = ta.trend.CCIIndicator(high, low, close, window=20).cci()

    # === Williams %R ===
    df['williams'] = ta.momentum.WilliamsRIndicator(high, low, close, lbp=14).williams_r()

    # === ATR (volatility) ===
    df['atr'] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    rsi       = latest['rsi']
    price     = latest['close']
    ema_fast  = latest['ema_fast']
    ema_slow  = latest['ema_slow']
    macd_diff = latest['macd_diff']
    macd_prev = prev['macd_diff']
    bb_upper  = latest['bb_upper']
    bb_lower  = latest['bb_lower']
    stoch_k   = latest['stoch_k']
    stoch_d   = latest['stoch_d']
    cci       = latest['cci']
    williams  = latest['williams']
    atr       = latest['atr']

    buy_score  = 0
    sell_score = 0
    total      = 8  # total indicators

    # 1. RSI
    if rsi < 30:
        buy_score += 1
    elif rsi > 70:
        sell_score += 1

    # 2. EMA Cross
    if ema_fast > ema_slow:
        buy_score += 1
    elif ema_fast < ema_slow:
        sell_score += 1

    # 3. MACD momentum
    if macd_diff > 0 and macd_diff > macd_prev:
        buy_score += 1
    elif macd_diff < 0 and macd_diff < macd_prev:
        sell_score += 1

    # 4. Bollinger Bands
    if price <= bb_lower:
        buy_score += 1
    elif price >= bb_upper:
        sell_score += 1

    # 5. Stochastic
    if stoch_k < 20 and stoch_d < 20:
        buy_score += 1
    elif stoch_k > 80 and stoch_d > 80:
        sell_score += 1

    # 6. CCI
    if cci < -100:
        buy_score += 1
    elif cci > 100:
        sell_score += 1

    # 7. Williams %R
    if williams < -80:
        buy_score += 1
    elif williams > -20:
        sell_score += 1

    # 8. Price vs EMA slow
    if price > ema_slow:
        buy_score += 1
    elif price < ema_slow:
        sell_score += 1

    dominant_score = max(buy_score, sell_score)
    direction = "buy" if buy_score >= sell_score else "sell"

    # === Success probability ===
    base_prob = (dominant_score / total) * 100
    # Volatility adjustment: lower ATR relative to price = more stable = higher prob
    volatility_ratio = (atr / price) * 1000
    vol_bonus = max(0, 5 - volatility_ratio)
    probability = min(95, round(base_prob + vol_bonus))

    # === Trade duration ===
    if dominant_score >= 7:
        duration = "5 - 10 دقائق"
    elif dominant_score >= 5:
        duration = "10 - 15 دقيقة"
    elif dominant_score >= 3:
        duration = "15 - 30 دقيقة"
    else:
        duration = "غير محدد"

    # === Signal strength label ===
    stars = "⭐" * dominant_score + "☆" * (total - dominant_score)

    # === Format indicators bar ===
    rsi_bar = _bar(rsi, 0, 100)

    details = (
        f"\n\n📊 *تحليل المؤشرات ({dominant_score}/{total}):*\n"
        f"• RSI `{rsi:.1f}` {rsi_bar}\n"
        f"• EMA: {'📈 صاعد' if ema_fast > ema_slow else '📉 هابط'}\n"
        f"• MACD: {'↑ إيجابي' if macd_diff > 0 else '↓ سلبي'}\n"
        f"• Bollinger: {'عند الدعم 🟢' if price <= bb_lower else 'عند المقاومة 🔴' if price >= bb_upper else 'وسط النطاق ⚪'}\n"
        f"• Stochastic: `{stoch_k:.1f}` {'ذروة بيع' if stoch_k < 20 else 'ذروة شراء' if stoch_k > 80 else 'محايد'}\n"
        f"• CCI: `{cci:.0f}` {'↑' if cci > 0 else '↓'}\n"
        f"• Williams %R: `{williams:.1f}`\n\n"
        f"⏱ *مدة الصفقة المقترحة:* {duration}\n"
        f"🎯 *نسبة النجاح المتوقعة:* `{probability}%`\n"
        f"💪 *قوة الإشارة:* {stars}"
    )

    if direction == "buy" and dominant_score >= 6:
        return f"🔼 *إشارة شراء قوية جداً* 🚀{details}"
    elif direction == "buy" and dominant_score >= 4:
        return f"🔼 *إشارة شراء* ✅{details}"
    elif direction == "sell" and dominant_score >= 6:
        return f"🔽 *إشارة بيع قوية جداً* 🚀{details}"
    elif direction == "sell" and dominant_score >= 4:
        return f"🔽 *إشارة بيع* ✅{details}"
    else:
        return f"⚠️ *السوق محايد — لا تدخل الآن*{details}"

def _bar(value, min_val, max_val, length=8):
    pct = (value - min_val) / (max_val - min_val)
    filled = max(0, min(length, int(pct * length)))
    return f"[{'█' * filled}{'░' * (length - filled)}]"

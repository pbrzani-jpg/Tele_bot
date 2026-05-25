# bot.py

import json
import os
import logging
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, CallbackQueryHandler
)
from apscheduler.schedulers.background import BackgroundScheduler
from config import TELEGRAM_BOT_TOKEN
from data_fetch import get_price, get_ohlc_data
from signal_engine import get_signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUBSCRIBERS_FILE = "subscribers.json"
SIGNAL_INTERVAL_MINUTES = 5

FOREX_PAIRS = [
    ["USD/JPY", "EUR/JPY", "EUR/USD"],
    ["GBP/JPY", "AUD/JPY", "CAD/JPY"],
    ["CHF/JPY", "EUR/AUD", "AUD/CAD"],
    ["AUD/CHF", "EUR/CAD", "EUR/CHF"],
    ["GBP/USD", "USD/CAD", "AUD/USD"],
    ["GBP/AUD", "EUR/GBP", "GBP/CAD"],
    ["GBP/CHF", "USD/CHF"],
]

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(subs, f)

subscribers = load_subscribers()

def get_user_pair(chat_id: str) -> str:
    return subscribers.get(str(chat_id), {}).get("pair", "CHF/JPY")

def is_subscribed(chat_id: str) -> bool:
    return subscribers.get(str(chat_id), {}).get("subscribed", False)

def pair_keyboard():
    keyboard = []
    for row in FOREX_PAIRS:
        keyboard.append([
            InlineKeyboardButton(pair, callback_data=f"pair:{pair}")
            for pair in row
        ])
    return InlineKeyboardMarkup(keyboard)

def fetch_signal_message(symbol: str) -> str:
    df = get_ohlc_data(symbol)
    if df is None:
        return f"❌ تعذّر جلب بيانات {symbol}، حاول لاحقاً."
    price = get_price(symbol)
    sig = get_signal(df)
    return f"💱 *{symbol}* — `{price:.4f}`\n{sig}"

def send_auto_signals(bot):
    for chat_id, data in list(subscribers.items()):
        if not data.get("subscribed", False):
            continue
        symbol = data.get("pair", "CHF/JPY")
        try:
            msg = fetch_signal_message(symbol)
            bot.send_message(chat_id=int(chat_id), text=msg, parse_mode='Markdown')
            logger.info(f"Auto signal → {chat_id} [{symbol}]")
        except Exception as e:
            logger.warning(f"Failed {chat_id}: {e}")

def start(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    if chat_id not in subscribers:
        subscribers[chat_id] = {"pair": "CHF/JPY", "subscribed": True}
    else:
        subscribers[chat_id]["subscribed"] = True
    save_subscribers(subscribers)
    pair = get_user_pair(chat_id)
    update.message.reply_text(
        f"👋 *مرحباً في بوت تحليل الفوركس!*\n\n"
        f"📌 الزوج الحالي: *{pair}*\n"
        f"✅ الإشارات التلقائية كل *{SIGNAL_INTERVAL_MINUTES} دقائق*\n\n"
        f"*الأوامر:*\n"
        f"📈 /signal — تحليل فوري\n"
        f"🔄 /setpair — تغيير زوج العملة\n"
        f"🔔 /subscribe — تفعيل الإشارات التلقائية\n"
        f"🔕 /stop — إيقاف الإشارات التلقائية",
        parse_mode='Markdown'
    )

def set_pair(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🔄 *اختر زوج العملة:*",
        reply_markup=pair_keyboard(),
        parse_mode='Markdown'
    )

def pair_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    chat_id = str(query.message.chat_id)
    symbol = query.data.split(":")[1]
    if chat_id not in subscribers:
        subscribers[chat_id] = {"pair": symbol, "subscribed": True}
    else:
        subscribers[chat_id]["pair"] = symbol
    save_subscribers(subscribers)
    query.edit_message_text(
        f"✅ تم اختيار *{symbol}*\n"
        f"سيصلك التحليل كل *{SIGNAL_INTERVAL_MINUTES} دقائق* تلقائياً\n\n"
        f"اكتب /signal لتحليل فوري الآن!",
        parse_mode='Markdown'
    )

def subscribe(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    if chat_id not in subscribers:
        subscribers[chat_id] = {"pair": "CHF/JPY", "subscribed": True}
    else:
        subscribers[chat_id]["subscribed"] = True
    save_subscribers(subscribers)
    pair = get_user_pair(chat_id)
    update.message.reply_text(
        f"🔔 تم تفعيل الإشارات!\n"
        f"الزوج: *{pair}* — كل *{SIGNAL_INTERVAL_MINUTES} دقائق*\n"
        f"لتغيير الزوج: /setpair",
        parse_mode='Markdown'
    )

def stop(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    if chat_id in subscribers:
        subscribers[chat_id]["subscribed"] = False
        save_subscribers(subscribers)
    update.message.reply_text("🔕 توقفت الإشارات. أعد التفعيل بـ /subscribe")

def signal_cmd(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    symbol = get_user_pair(chat_id)
    msg = update.message.reply_text(f"⏳ جاري تحليل *{symbol}*...", parse_mode='Markdown')
    result = fetch_signal_message(symbol)
    msg.edit_text(result, parse_mode='Markdown')

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("setpair", set_pair))
    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("signal", signal_cmd))
    dp.add_handler(CallbackQueryHandler(pair_callback, pattern="^pair:"))

    scheduler = BackgroundScheduler(timezone=pytz.utc)
    scheduler.add_job(
        send_auto_signals, 'interval',
        minutes=SIGNAL_INTERVAL_MINUTES,
        args=[updater.bot]
    )
    scheduler.start()
    logger.info(f"Scheduler started — every {SIGNAL_INTERVAL_MINUTES} min")

    updater.start_polling()
    logger.info("Bot running...")
    updater.idle()

if __name__ == "__main__":
    main()

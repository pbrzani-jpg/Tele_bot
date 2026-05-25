# bot.py

import json
import os
import logging
import pytz
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from config import TELEGRAM_BOT_TOKEN
from data_fetch import get_chfjpy_price, get_ohlc_data
from signal_engine import get_signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUBSCRIBERS_FILE = "subscribers.json"
SIGNAL_INTERVAL_MINUTES = 5

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_subscribers(subscribers):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subscribers), f)

subscribers = load_subscribers()

def build_signal_message():
    df = get_ohlc_data()
    if df is None:
        return None, "❌ Failed to retrieve data. Try again later."
    sig = get_signal(df)
    price = get_chfjpy_price()
    msg = (
        f"📊 *تحديث تلقائي — CHF/JPY*\n"
        f"💱 السعر: `{price:.3f}`\n"
        f"{sig}"
    )
    return price, msg

def send_auto_signals(bot):
    if not subscribers:
        return
    _, msg = build_signal_message()
    for chat_id in list(subscribers):
        try:
            bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
            logger.info(f"Auto signal sent to {chat_id}")
        except Exception as e:
            logger.warning(f"Failed to send to {chat_id}: {e}")
            subscribers.discard(chat_id)
            save_subscribers(subscribers)

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    save_subscribers(subscribers)
    update.message.reply_text(
        "👋 *مرحباً بك في بوت CHF/JPY!*\n\n"
        "✅ تم تفعيل الإشارات التلقائية كل *5 دقائق*\n\n"
        "الأوامر المتاحة:\n"
        "📈 /signal — إشارة فورية الآن\n"
        "🔔 /subscribe — تفعيل الإشارات التلقائية\n"
        "🔕 /stop — إيقاف الإشارات التلقائية",
        parse_mode='Markdown'
    )

def subscribe(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    save_subscribers(subscribers)
    update.message.reply_text(
        "🔔 تم تفعيل الإشارات التلقائية!\n"
        f"سيصلك تحديث كل *{SIGNAL_INTERVAL_MINUTES} دقائق* تلقائياً.",
        parse_mode='Markdown'
    )

def stop(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    subscribers.discard(chat_id)
    save_subscribers(subscribers)
    update.message.reply_text("🔕 تم إيقاف الإشارات التلقائية. يمكنك إعادة التفعيل بـ /subscribe")

def signal_cmd(update: Update, context: CallbackContext):
    df = get_ohlc_data()
    if df is None:
        update.message.reply_text("❌ تعذّر جلب البيانات، حاول مرة أخرى.")
        return
    sig = get_signal(df)
    price = get_chfjpy_price()
    update.message.reply_text(
        f"📈 *CHF/JPY*: `{price:.3f}`\n{sig}",
        parse_mode='Markdown'
    )

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("signal", signal_cmd))

    scheduler = BackgroundScheduler(timezone=pytz.utc)
    scheduler.add_job(
        send_auto_signals,
        'interval',
        minutes=SIGNAL_INTERVAL_MINUTES,
        args=[updater.bot]
    )
    scheduler.start()
    logger.info(f"Auto signal scheduler started — every {SIGNAL_INTERVAL_MINUTES} minutes")

    updater.start_polling()
    logger.info("Bot is running...")
    updater.idle()

if __name__ == "__main__":
    main()

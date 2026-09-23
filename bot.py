import os
import json
import logging
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- WEB SERVER ДЛЯ RENDER ---
app = Flask(__name__)
@app.route('/')
def home(): return "PS-21 Bot is alive!"
@app.route('/health')
def health(): return "OK"

def run_web():
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)

# --- ЗАГРУЗКА РАСПИСАНИЯ ---
with open("schedule.json", "r", encoding="utf-8") as f:
    SCHEDULE = json.load(f)

DAYS = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця"]
DAY_SHORT = {"Понеділок": "Пн", "Вівторок": "Вт", "Середа": "Ср", "Четвер": "Чт", "П'ятниця": "Пт"}
WEEK_NAMES = {"chys": "Чисельник", "znam": "Знаменник", "all": "Всі тижні"}

# --- КЛАВИАТУРЫ ---
def get_week_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Чисельник (непарний)", callback_data="week_chys")],
        [InlineKeyboardButton("⚪ Знаменник (парний)", callback_data="week_znam")],
        [InlineKeyboardButton("📅 Всі тижні", callback_data="week_all")]
    ])

def get_days_kb(week_param):
    row1 = [InlineKeyboardButton(DAY_SHORT[d], callback_data=f"day_{d}_{week_param}") for d in DAYS[:3]]
    row2 = [InlineKeyboardButton(DAY_SHORT[d], callback_data=f"day_{d}_{week_param}") for d in DAYS[3:]]
    back = [InlineKeyboardButton("🔙 Змінити тиждень", callback_data="back_weeks")]
    return InlineKeyboardMarkup([row1, row2, back])

# --- ХЕНДЛЕРЫ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "👋 Привіт! Це розклад для групи <b>ПС-21</b> (НЛТУ).\n\nОберіть тиждень:"
    await update.effective_message.reply_text(text, reply_markup=get_week_kb(), parse_mode="HTML")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "back_weeks":
        await query.edit_message_text("Оберіть тиждень:", reply_markup=get_week_kb())
        return

    if data.startswith("week_"):
        week_param = data.split("_")[1]
        text = f"🎓 Група <b>ПС-21</b>\n📅 Тиждень: <b>{WEEK_NAMES[week_param]}</b>\n\nОберіть день:"
        await query.edit_message_text(text, reply_markup=get_days_kb(week_param), parse_mode="HTML")
        return

    if data.startswith("day_"):
        _, day_name, week_param = data.split("_")
        pairs = SCHEDULE.get(day_name, [])
        
        # Фильтрация по неделе
        filtered = [p for p in pairs if p["week"] == "all" or p["week"] == week_param or week_param == "all"]

        if not filtered:
            msg = f"📅 <b>{day_name}</b> ({WEEK_NAMES[week_param]})\n\n🎉 Пар немає! Вільний день."
        else:
            msg = f"📅 <b>{day_name}</b> ({WEEK_NAMES[week_param]})\n\n"
            for p in filtered:
                w_mark = " <i>(чис.)</i>" if p["week"] == "chys" else (" <i>(знам.)</i>" if p["week"] == "znam" else "")
                msg += f"⏰ <b>{p['num']} пара ({p['time']})</b>{w_mark}\n📖 {p['text']}\n──────────────\n"

        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 До днів тижня", callback_data=f"week_{week_param}")]])
        await query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")

# --- СТАРТ ---
if __name__ == "__main__":
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("No TELEGRAM_TOKEN specified!")

    threading.Thread(target=run_web, daemon=True).start()

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buttons))
    application.run_polling(drop_pending_updates=True)

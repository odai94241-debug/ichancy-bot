import os
import sqlite3
from datetime import datetime

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from flask import Flask, request

BOT_TOKEN = "8734379872:AAHmapUaiR7aP7pPrcAmqaskQq1bWm7_BmQ"
ADMIN_ID = 7753870725

MIN_DEPOSIT = 200
MIN_WITHDRAWAL = 500

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__) 
DB_PATH = "bot_data.db"

def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = db_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('sham_cash','ضع_كود_الشام_كاش')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('syriatel_cash','ضع_كود_سيرياتيل')")
    conn.commit()
    conn.close()

init_db()

def get_setting(k):
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (k,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else ""

def set_setting(k, v):
    conn = db_conn()
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key,value) VALUES (?,?)", (k, v))
    conn.commit()
    conn.close()

def get_user(uid):
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

def update_balance(uid, amt):
    conn = db_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
    conn.commit()
    conn.close()

def main_menu(is_admin=False):
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(KeyboardButton("👤 حسابي"), KeyboardButton("💳 سحب رصيد من البوت"), KeyboardButton("📱 شحن رصيد في البوت"), KeyboardButton("🎧 الدعم"))
    if is_admin:
        m.add(KeyboardButton("⚙️ لوحة تحكم الآدمن"))
    return m

def back_menu():
    return ReplyKeyboardMarkup(row_width=1, resize_keyboard=True).add(KeyboardButton("🔙 رجوع"))

@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.chat.id
    bal = get_user(uid)
    text = f"✨ القائمة الرئيسية\n\n💰 الرصيد: {bal} ليرة جديدة\n🆔 ايديك: {uid}"
    bot.send_message(uid, text, reply_markup=main_menu(uid == ADMIN_ID))

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_all(message):
    uid = message.chat.id
    text = message.text or ""

    if text == "🔙 رجوع":
        bal = get_user(uid)
        bot.send_message(uid, f"القائمة الرئيسية:\n💰 الرصيد: {bal} ليرة", reply_markup=main_menu(uid == ADMIN_ID))
        return

    if text == "📱 شحن رصيد في البوت":
        bot.send_message(uid, f"💳 كود الشام كاش:\n`{get_setting('sham_cash')}`\n\nأرسل رقم عملية التحويل:", reply_markup=back_menu(), parse_mode="Markdown")
        return
        
    if text == "⚙️ لوحة تحكم الآدمن" and uid == ADMIN_ID:
        m = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        m.add(KeyboardButton("📱 تغيير كود الشام كاش"), KeyboardButton("📱 تغيير كود سيرياتيل كاش"), KeyboardButton("🔙 رجوع"))
        bot.send_message(uid, "لوحة التحكم:", reply_markup=m)
        return

    if text == "📱 تغيير كود الشام كاش" and uid == ADMIN_ID:
        set_setting("sham_cash", text)
        bot.send_message(uid, "✅ تم تحديث كود الشام كاش بنجاح.", reply_markup=main_menu(True))
        return
        
    if text == "📱 تغيير كود سيرياتيل كاش" and uid == ADMIN_ID:
        set_setting("syriatel_cash", text)
        bot.send_message(uid, "✅ تم تحديث كود سيرياتيل بنجاح.", reply_markup=main_menu(True))
        return

# ==================== Webhook ====================
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

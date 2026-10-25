import os
import sqlite3
from datetime import date

import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from flask import Flask, request

# ==================== الإعدادات ====================
TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7753870725"))
AGENT_CODE = os.getenv("AGENT_CODE", "")
ICHANCY_PANEL_URL = os.getenv("ICHANCY_PANEL_URL", "https://agents.ichancy.com")

MIN_DEPOSIT = int(os.getenv("MIN_DEPOSIT", "250"))
MIN_WITHDRAWAL = int(os.getenv("MIN_WITHDRAWAL", "500"))
WHEEL_DEPOSIT_REQUIRED = int(os.getenv("WHEEL_DEPOSIT_REQUIRED", "750"))
REFERRAL_PROFIT_SHARE = float(os.getenv("REFERRAL_PROFIT_SHARE", "0.05"))

# ==================== التهيئة ====================
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
DB_PATH = "bot_data.db"


# ==================== قاعدة البيانات ====================
def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        balance REAL DEFAULT 0,
        daily_deposit REAL DEFAULT 0,
        total_deposited REAL DEFAULT 0,
        total_withdrawn REAL DEFAULT 0,
        last_deposit_date TEXT,
        last_spin_date TEXT,
        referred_by INTEGER
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS accounts (
        user_id INTEGER,
        username TEXT,
        password TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance', 'off')")
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('sham_cash', 'غير محدد')")
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('syriatel_cash', 'غير محدد')")
    conn.commit()
    conn.close()


init_db()


def get_setting(key):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""


def set_setting(key, value):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def add_user(user_id, first_name, referred_by=None):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, first_name, referred_by) VALUES (?, ?, ?)",
        (user_id, first_name, referred_by),
    )
    conn.commit()
    conn.close()


def get_user_info(user_id):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT balance, daily_deposit, last_deposit_date, last_spin_date FROM users WHERE user_id=?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    today = str(date.today())
    if row:
        balance, daily_dep, last_dep_date, last_spin = row
        if last_dep_date != today:
            daily_dep = 0
        return balance, daily_dep, last_dep_date, last_spin
    return 0, 0, "", ""


def update_user_balance(user_id, amount):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def add_user_deposit(user_id, amount):
    today = str(date.today())
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT daily_deposit, last_deposit_date, total_deposited FROM users WHERE user_id=?",
        (user_id,),
    )
    row = cursor.fetchone()
    if row:
        current_dep, last_date, total_dep = row
        new_daily = (current_dep + amount) if last_date == today else amount
        new_total = total_dep + amount
        cursor.execute(
            "UPDATE users SET daily_deposit = ?, last_deposit_date = ?, total_deposited = ? WHERE user_id=?",
            (new_daily, today, new_total, user_id),
        )
        conn.commit()
    conn.close()


def calculate_referral_earnings(referrer_id):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, total_deposited, total_withdrawn FROM users WHERE referred_by=?",
        (referrer_id,),
    )
    referrals = cursor.fetchall()
    conn.close()
    total_ref_count = len(referrals)
    total_net_loss = 0
    for u_id, dep, withdr in referrals:
        net = dep - withdr
        if net > 0:
            total_net_loss += net
    earnings = total_net_loss * REFERRAL_PROFIT_SHARE
    return total_ref_count, earnings, total_net_loss


def save_player_account(user_id, username, password):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts VALUES (?, ?, ?)", (user_id, username, password))
    conn.commit()
    conn.close()


def get_player_account(user_id):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM accounts WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_all_users():
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def calculate_withdrawal_commission(amount):
    if amount <= 500000:
        rate = 0.10
    elif amount <= 1500000:
        rate = 0.15
    else:
        rate = 0.20
    deduction = amount * rate
    return amount - deduction, rate * 100


# ==================== Keyboards ====================
def main_menu(is_admin=False):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("⚡ حساب إيشَانسي وشحنه"),
        KeyboardButton("💳 سحب رصيد من البوت"),
        KeyboardButton("📱 شحن رصيد في البوت"),
        KeyboardButton("🎁 كود جائزة"),
        KeyboardButton("🤝 إهداء صديق"),
        KeyboardButton("👥 الإحالات"),
        KeyboardButton("📊 السجلات"),
        KeyboardButton("🌐 إيشَانسي"),
        KeyboardButton("🔄 استرداد آخر طلب سحب"),
        KeyboardButton("🎁 العروض النشطة"),
        KeyboardButton("📜 شروط الاستخدام"),
        KeyboardButton("🎧 إرسال رسالة للدعم"),
        KeyboardButton("🎡 عجلة الفرصة"),
    )
    if is_admin:
        markup.add(KeyboardButton("⚙️ لوحة تحكم الآدمن"))
    return markup


def ichancy_sub_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("👤 إنشاء حساب إيشَانسي"),
        KeyboardButton("💳 شحن رصيد من الحساب"),
        KeyboardButton("💸 سحب رصيد من الحساب"),
        KeyboardButton("⚡ شحن كامل الرصيد"),
        KeyboardButton("🗑️ حذف حساب إيشَانسي"),
        KeyboardButton("🔙 رجوع للقائمة الرئيسية"),
    )
    return markup


def admin_panel_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    status = "إيقاف الصيانة 🔴" if get_setting("maintenance") == "on" else "تشغيل الصيانة 🟢"
    markup.add(
        KeyboardButton(f"🛠️ {status}"),
        KeyboardButton("📢 إرسال إذاعة للجميع"),
        KeyboardButton("📱 تغيير كود الشام كاش"),
        KeyboardButton("📱 تغيير كود سيريتل كاش"),
        KeyboardButton("👥 إحصائيات الأعضاء"),
        KeyboardButton("🔙 رجوع للقائمة الرئيسية"),
    )
    return markup


def back_menu():
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(KeyboardButton("🔙 رجوع للقائمة الرئيسية"))
    return markup


# ==================== Handlers ====================
user_states = {}
temp_data = {}


@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.chat.id
    args = message.text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    add_user(user_id, message.from_user.first_name, ref_id)
    user_states[user_id] = None
    is_admin = user_id == ADMIN_ID
    if get_setting("maintenance") == "on" and not is_admin:
        bot.send_message(user_id, "⚠️ البوت قيد الصيانة حالياً.")
        return
    balance, _, _, _ = get_user_info(user_id)
    text = (
        f"✨ **قائمة الخيارات الرئيسية**\n\n"
        f"💰 **الرصيد الحالي:** {balance} ليرة جديدة\n"
        f"🆔 **الآيدي الخاص بك:** `{user_id}`"
    )
    bot.send_message(user_id, text, reply_markup=main_menu(is_admin), parse_mode="Markdown")


@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_all_messages(message):
    user_id = message.chat.id
    text = message.text if message.text else ""
    is_admin = user_id == ADMIN_ID

    if get_setting("maintenance") == "on" and not is_admin:
        bot.send_message(user_id, "⚠️ البوت قيد الصيانة حالياً.")
        return

    state = user_states.get(user_id)

    if state == "awaiting_ichancy_reg_username":
        temp_data[user_id] = {"username": text}
        user_states[user_id] = "awaiting_ichancy_reg_password"
        bot.send_message(user_id, "🔐 أرسل كلمة المرور للحساب الجديد (6 خانات على الأقل):", reply_markup=back_menu())
        return

    if state == "awaiting_ichancy_reg_password":
        username = temp_data.get(user_id, {}).get("username")
        password = text
        user_states[user_id] = None
        temp_data.pop(user_id, None)
        save_player_account(user_id, username, password)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌐 الدخول الفوري إلى iChancy", url=ICHANCY_PANEL_URL))
        bot.send_message(
            user_id,
            f"✅ **تم إنشاء الحساب بنجاح!** 🎉\n\n"
            f"• اسم المستخدم: `{username}`\n• كلمة المرور: `{password}`",
            reply_markup=markup, parse_mode="Markdown",
        )
        return

    if state == "awaiting_deposit_amount":
        try:
            amount = float(text)
        except ValueError:
            bot.send_message(user_id, "⚠️ يرجى إرسال رقم صحيح للمبلغ!")
            return
        if amount < MIN_DEPOSIT and not is_admin:
            bot.send_message(user_id, f"⚠️ عذراً، الحد الأدنى للشحن هو **{MIN_DEPOSIT} ليرة جديدة**!", parse_mode="Markdown")
            return
        user_states[user_id] = None
        add_user_deposit(user_id, amount)
        bonus = amount * 0.10
        total = amount + bonus
        update_user_balance(user_id, total)
        bot.send_message(
            user_id,
            f"✅ **تم الشحن بنجاح!**\n• المبلغ: {amount} ليرة\n• البونص: {bonus} ليرة\n• الإجمالي: {total} ليرة جديدة",
            reply_markup=main_menu(is_admin), parse_mode="Markdown",
        )
        return

    if state == "awaiting_withdraw_amount":
        try:
            amount = float(text)
        except ValueError:
            bot.send_message(user_id, "⚠️ يرجى إرسال رقم صحيح للمبلغ!")
            return
        if amount < MIN_WITHDRAWAL and not is_admin:
            bot.send_message(user_id, f"⚠️ عذراً، الحد الأدنى للسحب هو **{MIN_WITHDRAWAL} ليرة جديدة**!", parse_mode="Markdown")
            return
        user_states[user_id] = None
        net_amount, rate = calculate_withdrawal_commission(amount)
        bot.send_message(
            ADMIN_ID,
            f"💸 **طلب سحب جديد:**\n• المستخدم: {user_id}\n• المبلغ: {amount} ليرة\n• الصافي: {net_amount} ليرة",
            parse_mode="Markdown",
        )
        bot.send_message(
            user_id,
            f"⏳ تم إرسال طلب سحبك.\n• الصافي بعد العمولة ({rate}%): **{net_amount} ليرة جديدة**",
            reply_markup=main_menu(is_admin), parse_mode="Markdown",
        )
        return

    if text == "🔙 رجوع للقائمة الرئيسية":
        user_states[user_id] = None
        bot.send_message(user_id, "القائمة الرئيسية:", reply_markup=main_menu(is_admin))
    elif text == "⚡ حساب إيشَانسي وشحنه":
        bot.send_message(user_id, "إدارة حساب iChancy:", reply_markup=ichancy_sub_menu())
    elif text == "👥 الإحالات":
        ref_count, earnings, net_loss = calculate_referral_earnings(user_id)
        ref_link = f"https://t.me/{(bot.get_me()).username}?start={user_id}"
        msg = (
            f"👥 **نظام الإحالات (5%):**\n\n"
            f"• عدد المدعويين: `{ref_count}` لاعبين\n"
            f"• صافي خسارة الإحالات: `{net_loss}` ليرة\n"
            f"• أرباحك (5%): **{earnings} ليرة جديدة**\n\n"
            f"🔗 **رابط الإحالة:**\n`{ref_link}`"
        )
        bot.send_message(user_id, msg, parse_mode="Markdown", reply_markup=back_menu())
    elif text == "👤 إنشاء حساب إيشَانسي":
        acc = get_player_account(user_id)
        if acc:
            bot.send_message(user_id, f"⚠️ لديك حساب مسجل:\n• اليوزر: `{acc[0]}`\n• الباسورد: `{acc[1]}`", parse_mode="Markdown")
        else:
            user_states[user_id] = "awaiting_ichancy_reg_username"
            bot.send_message(user_id, "👤 أرسل اسم المستخدم الجديد لحساب iChancy:", reply_markup=back_menu())
    elif text == "📱 شحن رصيد في البوت":
        user_states[user_id] = "awaiting_deposit_amount"
        bot.send_message(user_id, f"💵 أرسل قيمة المبلغ (الحد الأدنى {MIN_DEPOSIT} ليرة):", reply_markup=back_menu())
    elif text == "💳 سحب رصيد من البوت":
        user_states[user_id] = "awaiting_withdraw_amount"
        bot.send_message(user_id, f"💵 أرسل المبلغ للسحب (الحد الأدنى {MIN_WITHDRAWAL} ليرة):", reply_markup=back_menu())


# ==================== Webhook (الجزء الجديد) ====================
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


@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    """افتح هذا الرابط مرة واحدة من المتصفح لتفعيل Webhook"""
    url = os.getenv("RENDER_EXTERNAL_URL", "") + "/webhook"
    if not url.startswith("http"):
        return "RENDER_EXTERNAL_URL غير مضبوط", 400
    result = bot.set_webhook(url=url)
    return f"Webhook set to {url} | result={result}", 200


@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    bot.remove_webhook()
    return "Webhook deleted", 200


# ==================== تشغيل ====================
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

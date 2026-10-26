import os
import sqlite3
from datetime import datetime

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from flask import Flask, request

# التوكن اللي إنت حاططه حالياً
BOT_TOKEN = "8734379872:AAHmapUaiR7aP7pPrcAmqaskQq1bWm7_BmQ"
ADMIN_ID = 7753870725
ICHANCY_PANEL_URL = "https://agents.ichancy.com"

MIN_DEPOSIT = 200
MIN_WITHDRAWAL = 500
REFERRAL_PROFIT_SHARE = 0.05
REFERRAL_MIN_ACTIVE = 3

# هدول السطرين هني اللي كانوا ناقصين وسببوا المشكلة
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__) 
DB_PATH = "bot_data.db"

# ==================== قاعدة البيانات ====================
def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = db_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, first_name TEXT,
        balance REAL DEFAULT 0, total_deposited REAL DEFAULT 0,
        total_withdrawn REAL DEFAULT 0, referred_by INTEGER,
        created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS accounts (
        user_id INTEGER PRIMARY KEY, username TEXT, password TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance','off')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('sham_cash','غير محدد')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('syriatel_cash','غير محدد')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('usd_rate','140')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('terms', 'شروط الاستخدام — odai Robert')")
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

def add_user(uid, name, ref=None):
    conn = db_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id,first_name,referred_by,created_at) VALUES (?,?,?,?)", (uid, name, ref, str(datetime.now())))
    conn.commit()
    conn.close()

def get_user(uid):
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT balance,total_deposited,total_withdrawn,referred_by FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    conn.close()
    return r if r else (0, 0, 0, None)

def update_balance(uid, amt):
    conn = db_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
    conn.commit()
    conn.close()

def save_account(uid, u, p):
    conn = db_conn()
    c = conn.cursor()
    c.execute("REPLACE INTO accounts VALUES (?,?,?)", (uid, u, p))
    conn.commit()
    conn.close()

def get_account(uid):
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT username,password FROM accounts WHERE user_id=?", (uid,))
    r = c.fetchone()
    conn.close()
    return r

def get_all_users():
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    r = c.fetchall()
    conn.close()
    return [x[0] for x in r]

# ==================== الأزرار ====================
def main_menu(is_admin=False):
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("👤 حسابي"), KeyboardButton("💳 سحب رصيد من البوت"),
        KeyboardButton("📱 شحن رصيد في البوت"), KeyboardButton("🤝 إهداء صديق"),
        KeyboardButton("🎁 كود جائزة"), KeyboardButton("👥 الإحالات"),
        KeyboardButton("📊 السجلات"), KeyboardButton("🎧 إرسال رسالة للدعم"),
        KeyboardButton("🌐 ايشاني"), KeyboardButton("🔄 استرداد آخر طلب سحب"),
        KeyboardButton("🎁 العروض النشطة"), KeyboardButton("📜 شروط الاستخدام"),
        KeyboardButton("🎡 عجلة الفرصة"),
    )
    if is_admin:
        m.add(KeyboardButton("⚙️ لوحة تحكم الآدمن"))
    return m

def ichancy_menu():
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("👤 إنشاء حساب ايشاني"), KeyboardButton("💳 سحب رصيد من الحساب"),
        KeyboardButton("💳 شحن رصيد في الحساب"), KeyboardButton("⚡ شحن كامل الرصيد"),
        KeyboardButton("🗑️ حذف حسابي"), KeyboardButton("🔙 رجوع"),
    )
    return m

def withdraw_menu():
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("سيرياتيل كاش"), KeyboardButton("شام كاش"),
        KeyboardButton("هرم"), KeyboardButton("🔙 رجوع"),
    )
    return m

def deposit_menu():
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("سيرياتيل كاش"), KeyboardButton("شام كاش"),
        KeyboardButton("شام كاش USD"), KeyboardButton("🔙 رجوع"),
    )
    return m

def admin_menu():
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("🛠️ إيقاف/تشغيل الصيانة"), KeyboardButton("📢 إرسال إذاعة للجميع"),
        KeyboardButton("📱 تغيير كود الشام كاش"), KeyboardButton("📱 تغيير كود سيرياتيل كاش"),
        KeyboardButton("💵 تغيير سعر شام كاش دولار"), KeyboardButton("👥 إحصائيات الأعضاء"),
        KeyboardButton("🔙 رجوع"),
    )
    return m

def back_menu():
    m = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    m.add(KeyboardButton("🔙 رجوع"))
    return m

# ==================== الدوال المساعدة ====================
def calc_commission(amt):
    if amt <= 50000000: rate = 0.10
    elif amt <= 150000000: rate = 0.15
    else: rate = 0.20
    return amt - (amt * rate), rate * 100

# ==================== المعالجات ====================
user_states = {}
temp_data = {}

@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.chat.id
    args = message.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    add_user(uid, message.from_user.first_name, ref)
    user_states[uid] = None
    is_admin = uid == ADMIN_ID

    if ref and ref != uid:
        try: bot.send_message(ref, f"👥 إحالة جديدة!\n👤 شخص جديد دخل من رابطك")
        except: pass

    if get_setting("maintenance") == "on" and not is_admin:
        bot.send_message(uid, "⚠️ البوت قيد الصيانة حالياً.")
        return

    bal, _, _, _ = get_user(uid)
    text = f"✨ قائمة الخيارات الرئيسية\n\n💰 الرصيد: {bal} ليرة جديدة\n🆔 ايديك: {uid}"
    bot.send_message(uid, text, reply_markup=main_menu(is_admin))

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_all(message):
    uid = message.chat.id
    text = message.text or ""
    is_admin = uid == ADMIN_ID

    if get_setting("maintenance") == "on" and not is_admin:
        bot.send_message(uid, "⚠️ البوت قيد الصيانة حالياً.")
        return

    if text == "🔙 رجوع":
        user_states[uid] = None
        temp_data.pop(uid, None)
        bal, _, _, _ = get_user(uid)
        bot.send_message(uid, f"القائمة الرئيسية:\n💰 الرصيد: {bal} ليرة جديدة", reply_markup=main_menu(is_admin))
        return

    state = user_states.get(uid)

    if state == "reg_username":
        if not text.isascii() or not any(c.isdigit() for c in text):
            bot.send_message(uid, "⚠️ اسم المستخدم لازم إنجليزي وفيه رقم. جرب تاني:", reply_markup=back_menu())
            return
        temp_data[uid] = {"username": text}
        user_states[uid] = "reg_password"
        bot.send_message(uid, "🔐 أرسل كلمة السر (6 خانات على الأقل):", reply_markup=back_menu())
        return

    if state == "reg_password":
        if len(text) < 6:
            bot.send_message(uid, "⚠️ كلمة السر لازم 6 خانات على الأقل. جرب تاني:", reply_markup=back_menu())
            return
        username = temp_data.get(uid, {}).get("username")
        password = text
        user_states[uid] = None
        temp_data.pop(uid, None)
        bot.send_message(uid, "⏳ تم إرسال طلبك للإدارة، سيتم إنشاء الحساب قريباً.", reply_markup=main_menu(is_admin))
        admin_text = f"👤 طلب إنشاء حساب جديد\n\n🆔 ايدي الزبون: {uid}\n👤 اسم المستخدم: {username}\n🔑 كلمة السر: {password}\n\n👉 يرجى الدخول للموقع وإنشاء الحساب يدوياً."
        bot.send_message(ADMIN_ID, admin_text)
        return

    if state == "wd_amount":
        try: amt = float(text)
        except:
            bot.send_message(uid, "⚠️ أرسل رقم صحيح:", reply_markup=back_menu())
            return
        if amt < MIN_WITHDRAWAL:
            bot.send_message(uid, f"⚠️ الحد الأدنى {MIN_WITHDRAWAL} ليرة", reply_markup=back_menu())
            return
        bal, _, _, _ = get_user(uid)
        if amt > bal:
            bot.send_message(uid, f"⚠️ رصيدك {bal} ليرة، ما تكفي", reply_markup=back_menu())
            return
        temp_data[uid]["amount"] = amt
        user_states[uid] = "wd_account"
        bot.send_message(uid, "📝 أرسل رقم حسابك:", reply_markup=back_menu())
        return

    if state == "wd_account":
        amt = temp_data[uid]["amount"]
        method = temp_data[uid]["method"]
        net, rate = calc_commission(amt)
        update_balance(uid, -amt)
        user_states[uid] = None
        temp_data.pop(uid, None)
        bot.send_message(uid, f"⏳ تم إرسال طلب السحب\n💰 {amt}\n📉 العمولة: {rate}%\n✅ الصافي: {net} ليرة", reply_markup=main_menu(is_admin))
        bot.send_message(ADMIN_ID, f"💸 طلب سحب\n👤 {uid}\n💰 {amt}\n📉 {rate}%\n✅ {net}\n📱 {method}\n🔢 {text}")
        return

    if state == "dep_amount":
        try: amt = float(text)
        except:
            bot.send_message(uid, "⚠️ أرسل رقم صحيح:", reply_markup=back_menu())
            return
        if amt < MIN_DEPOSIT:
            bot.send_message(uid, f"⚠️ الحد الأدنى {MIN_DEPOSIT} ليرة", reply_markup=back_menu())
            return
        temp_data[uid]["amount"] = amt
        user_states[uid] = "dep_tx"
        bot.send_message(uid, "📝 أرسل رقم عملية التحويل:", reply_markup=back_menu())
        return

    if state == "dep_tx":
        amt = temp_data[uid]["amount"]
        method = temp_data[uid]["method"]
        user_states[uid] = None
        temp_data.pop(uid, None)
        bot.send_message(uid, f"⏳ تم إرسال طلب الشحن\n💰 {amt} ليرة\n\nبانتظار الموافقة", reply_markup=main_menu(is_admin))
        bot.send_message(ADMIN_ID, f"📥 طلب شحن\n👤 {uid}\n💰 {amt}\n📱 {method}\n🔢 {text}")
        return
        
    if text == "👤 حسابي":
        acc = get_account(uid)
        if acc: bot.send_message(uid, f"👤 حسابك\n\n👤 المستخدم: {acc[0]}\n🔑 كلمة السر: {acc[1]}", reply_markup=ichancy_menu())
        else: bot.send_message(uid, "ما عندك حساب. اضغط إنشاء حساب:", reply_markup=ichancy_menu())

    elif text == "👤 إنشاء حساب ايشاني":
        user_states[uid] = "reg_username"
        bot.send_message(uid, "👤 أرسل اسم المستخدم (إنجليزي + رقم):", reply_markup=back_menu())

    elif text == "💳 سحب رصيد من البوت":
        user_states[uid] = "wd_method"
        bot.send_message(uid, "💳 اختر طريقة السحب:", reply_markup=withdraw_menu())

    elif text in ("سيرياتيل كاش", "شام كاش", "هرم") and user_states.get(uid) == "wd_method":
        temp_data[uid] = {"method": text}
        user_states[uid] = "wd_amount"
        bot.send_message(uid, f"💵 أرسل المبلغ (الحد الأدنى {MIN_WITHDRAWAL} ليرة):", reply_markup=back_menu())

    elif text == "📱 شحن رصيد في البوت":
        user_states[uid] = "dep_method"
        bot.send_message(uid, "📱 اختر طريقة الشحن:", reply_markup=deposit_menu())

    elif text in ("سيرياتيل كاش", "شام كاش", "شام كاش USD") and user_states.get(uid) == "dep_method":
        temp_data[uid] = {"method": text}
        user_states[uid] = "dep_amount"
        bot.send_message(uid, f"💵 أرسل المبلغ (الحد الأدنى {MIN_DEPOSIT} ليرة):", reply_markup=back_menu())

    elif text == "👥 الإحالات":
        ref_link = f"https://t.me/{(bot.get_me()).username}?start={uid}"
        conn_users = get_all_users()
        total = len([u for u in conn_users if get_user(u)[3] == uid])
        active = len([u for u in conn_users if get_user(u)[3] == uid and get_user(u)[1] > 0])
        net = sum(max(0, get_user(u)[1] - get_user(u)[2]) for u in conn_users if get_user(u)[3] == uid)
        earnings = net * REFERRAL_PROFIT_SHARE if active >= REFERRAL_MIN_ACTIVE else 0
        msg = (f"👥 الإحالات\n\n🔗 رابطك: {ref_link}\n\n📊 إجمالي: {total}\n✅ نشطة: {active}\n💰 صافي خسارة: {net}\n🎁 أرباحك (5%): {earnings}\n\n⚠️ شرط: 3 إحالات نشطة على الأقل")
        bot.send_message(uid, msg, reply_markup=back_menu())

    elif text == "📊 السجلات":
        bot.send_message(uid, "📊 سجلاتك:\n\n(سيتم إضافة السجلات قريباً)", reply_markup=back_menu())

    elif text == "🎧 إرسال رسالة للدعم":
        user_states[uid] = "support"
        bot.send_message(uid, "🎧 أرسل رسالتك:", reply_markup=back_menu())

    elif text == "🌐 ايشاني":
        mk = InlineKeyboardMarkup()
        mk.add(InlineKeyboardButton("🌐 فتح الموقع", url=ICHANCY_PANEL_URL))
        bot.send_message(uid, "اضغط للدخول:", reply_markup=mk)

    elif text == "🔄 استرداد آخر طلب سحب":
        bot.send_message(uid, "🔄 ما في طلبات سحب معلقة حالياً", reply_markup=back_menu())

    elif text == "🎁 العروض النشطة":
        bot.send_message(uid, "ما في عروض نشطة حالياً", reply_markup=back_menu())

    elif text == "📜 شروط الاستخدام":
        bot.send_message(uid, get_setting("terms"), reply_markup=back_menu())

    elif text == "🎡 عجلة الفرصة":
        bot.send_message(uid, "🎡 عجلة الفرصة\n\n(سيتم إضافتها قريباً)", reply_markup=back_menu())

    elif text == "🤝 إهداء صديق":
        bot.send_message(uid, "🤝 إهداء صديق\n\n(سيتم إضافته قريباً)", reply_markup=back_menu())

    elif text == "🎁 كود جائزة":
        bot.send_message(uid, "🎁 أرسل كود الجائزة:\n\n(سيتم إضافته قريباً)", reply_markup=back_menu())

    elif text == "⚙️ لوحة تحكم الآدمن" and is_admin:
        bot.send_message(uid, "⚙️ لوحة التحكم:", reply_markup=admin_menu())

    elif text == "🛠️ إيقاف/تشغيل الصيانة" and is_admin:
        current = get_setting("maintenance")
        new = "off" if current == "on" else "on"
        set_setting("maintenance", new)
        bot.send_message(uid, f"✅ الصيانة: {new}", reply_markup=admin_menu())

    elif text == "📢 إرسال إذاعة للجميع" and is_admin:
        user_states[uid] = "broadcast"
        bot.send_message(uid, "📢 أرسل الرسالة:", reply_markup=back_menu())

    elif text == "📱 تغيير كود الشام كاش" and is_admin:
        user_states[uid] = "sham_update"
        bot.send_message(uid, "📱 أرسل كود الشام كاش الجديد:", reply_markup=back_menu())

    elif text == "📱 تغيير كود سيرياتيل كاش" and is_admin:
        user_states[uid] = "syriatel_update"
        bot.send_message(uid, "📱 أرسل كود سيرياتيل الجديد:", reply_markup=back_menu())

    elif text == "💵 تغيير سعر شام كاش دولار" and is_admin:
        user_states[uid] = "usd_rate_update"
        bot.send_message(uid, "💵 أرسل السعر الجديد (مثلاً: 140):", reply_markup=back_menu())

    elif text == "👥 إحصائيات الأعضاء" and is_admin:
        all_u = get_all_users()
        bot.send_message(uid, f"👥 عدد الأعضاء: {len(all_u)}", reply_markup=admin_menu())

    elif state == "broadcast" and is_admin:
        for u in get_all_users():
            try: bot.send_message(u, text)
            except: pass
        user_states[uid] = None
        bot.send_message(uid, "✅ تمت الإذاعة", reply_markup=admin_menu())

    elif state == "sham_update" and is_admin:
        set_setting("sham_cash", text)
        user_states[uid] = None
        bot.send_message(uid, f"✅ تم تحديث شام كاش: {text}", reply_markup=admin_menu())

    elif state == "syriatel_update" and is_admin:
        set_setting("syriatel_cash", text)
        user_states[uid] = None
        bot.send_message(uid, f"✅ تم تحديث سيرياتيل: {text}", reply_markup=admin_menu())

    elif state == "usd_rate_update" and is_admin:
        try:
            rate = float(text)
            set_setting("usd_rate", str(rate))
            user_states[uid] = None
            bot.send_message(uid, f"✅ تم تحديث السعر: {rate}", reply_markup=admin_menu())
        except:
            bot.send_message(uid, "⚠️ أرسل رقم صحيح:", reply_markup=back_menu())

    elif state == "support":
        bot.send_message(ADMIN_ID, f"🎧 رسالة دعم من {uid}:\n\n{text}")
        user_states[uid] = None
        bot.send_message(uid, "✅ تم إرسال رسالتك", reply_markup=main_menu(is_admin))


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

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    try:
        base_url = os.getenv("RENDER_EXTERNAL_URL", "https://ichancy-bot-2.onrender.com")
        url = base_url.rstrip("/") + "/webhook"
        result = bot.set_webhook(url=url)
        return f"Webhook set to {url} | result={result}", 200
    except Exception as e:
        return f"Error: {str(e)}", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

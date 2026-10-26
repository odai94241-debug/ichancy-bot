import os
import sqlite3
from datetime import datetime

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from flask import Flask, request

BOT_TOKEN = "8734379872:AAGuhAhKo3-6wxC3C7xrqhGL-3A5nPIEwxY"
ADMIN_ID = 7753870725

MIN_DEPOSIT = 200
MIN_WITHDRAWAL = 500
REFERRAL_PROFIT_SHARE = 0.05
REFERRAL_MIN_ACTIVE = 3

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__) 
DB_PATH = "bot_data.db"

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
    c.execute("""CREATE TABLE IF NOT EXISTS pending_deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, method TEXT, tx_id TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS pending_withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, method TEXT, account TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance','off')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('sham_cash','ضع_كود_الشام_كاش')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('syriatel_cash','ضع_كود_سيرياتيل')")
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
    m.add(KeyboardButton("سيرياتيل كاش"), KeyboardButton("شام كاش"), KeyboardButton("هرم"), KeyboardButton("🔙 رجوع"))
    return m

def deposit_menu():
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(KeyboardButton("سيرياتيل كاش"), KeyboardButton("شام كاش"), KeyboardButton("شام كاش USD"), KeyboardButton("🔙 رجوع"))
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

def calc_commission(amt):
    if amt <= 50000000: rate = 0.10
    elif amt <= 150000000: rate = 0.15
    else: rate = 0.20
    return amt - (amt * rate), rate * 100

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
        try: bot.send_message(ref, "👥 إحالة جديدة!\n👤 شخص جديد دخل من رابطك")
        except: pass

    if get_setting("maintenance") == "on" and not is_admin:
        bot.send_message(uid, "⚠️ البوت قيد الصيانة حالياً.")
        return

    bal, _, _, _ = get_user(uid)
    text = f"✨ قائمة الخيارات الرئيسية\n\n💰 الرصيد: {bal} ليرة جديدة\n🆔 ايديك: {uid}"
    bot.send_message(uid, text, reply_markup=main_menu(is_admin))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data
    if data.startswith("dep_ok_") or data.startswith("dep_no_"):
        parts = data.split("_")
        action = parts[1]
        dep_id = int(parts[2])
        
        conn = db_conn()
        c = conn.cursor()
        c.execute("SELECT user_id, amount FROM pending_deposits WHERE id=?", (dep_id,))
        row = c.fetchone()
        
        if row:
            user_id, amount = row
            if action == "ok":
                update_balance(user_id, amount)
                bot.send_message(user_id, f"✅ تمت الموافقة على طلب الشحن!\n💰 تم إضافة {amount} ليرة لرصيدك.")
                bot.edit_message_text(f"✅ تمت الموافقة على طلب الشحن للزبون {user_id} بمبلغ {amount}.", call.message.chat.id, call.message.message_id)
            else:
                bot.send_message(user_id, f"❌ تم رفض طلب الشحن الخاص بك.")
                bot.edit_message_text(f"❌ تم رفض طلب الشحن للزبون {user_id}.", call.message.chat.id, call.message.message_id)
            
            c.execute("DELETE FROM pending_deposits WHERE id=?", (dep_id,))
            conn.commit()
        conn.close()
        bot.answer_callback_query(call.id)

    elif data.startswith("wd_ok_") or data.startswith("wd_no_"):
        parts = data.split("_")
        action = parts[1]
        wd_id = int(parts[2])
        
        conn = db_conn()
        c = conn.cursor()
        c.execute("SELECT user_id, amount FROM pending_withdrawals WHERE id=?", (wd_id,))
        row = c.fetchone()
        
        if row:
            user_id, amount = row
            if action == "ok":
                bot.send_message(user_id, f"✅ تمت الموافقة على طلب السحب!\n💰 تم تحويل {amount} ليرة لحسابك.")
                bot.edit_message_text(f"✅ تمت الموافقة على السحب للزبون {user_id} بمبلغ {amount}.", call.message.chat.id, call.message.message_id)
            else:
                update_balance(user_id, amount)
                bot.send_message(user_id, f"❌ تم رفض طلب السحب الخاص بك.\n💰 تم إرجاع {amount} ليرة إلى رصيدك.")
                bot.edit_message_text(f"❌ تم رفض السحب للزبون {user_id} وإرجاع الرصيد.", call.message.chat.id, call.message.message_id)
            
            c.execute("DELETE FROM pending_withdrawals WHERE id=?", (wd_id,))
            conn.commit()
        conn.close()
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_all(message):
    uid = message.chat.id
    text = message.text or ""
    is_admin = uid == ADMIN_ID

    if text == "🔙 رجوع":
        user_states[uid] = None
        temp_data.pop(uid, None)
        bal, _, _, _ = get_user(uid)
        bot.send_message(uid, f"القائمة الرئيسية:\n💰 الرصيد: {bal} ليرة جديدة", reply_markup=main_menu(is_admin))
        return

    if user_states.get(uid) == "dep_tx":
        temp_data[uid]["tx"] = text
        user_states[uid] = "dep_amount"
        bot.send_message(uid, "💵 أرسل المبلغ اللي شحنته (الحد الأدنى 200 ليرة):", reply_markup=back_menu())
        return

    if user_states.get(uid) == "dep_amount":
        try: amt = float(text)
        except:
            bot.send_message(uid, "⚠️ أرسل رقم صحيح:", reply_markup=back_menu())
            return
        if amt < MIN_DEPOSIT:
            bot.send_message(uid, "⚠️ الحد الأدنى 200 ليرة", reply_markup=back_menu())
            return
        
        method = temp_data[uid]["method"]
        tx = temp_data[uid]["tx"]
        
        conn = db_conn()
        c = conn.cursor()
        c.execute("INSERT INTO pending_deposits (user_id, amount, method, tx_id) VALUES (?,?,?,?)", (uid, amt, method, tx))
        dep_id = c.lastrowid
        conn.commit()
        conn.close()

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ موافقة", callback_data=f"dep_ok_{dep_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"dep_no_{dep_id}"))
        
        msg_admin = f"📥 طلب شحن جديد\n\n👤 الزبون: {uid}\n📱 الطريقة: {method}\n🔢 رقم العملية: {tx}\n💰 المبلغ: {amt} ليرة"
        bot.send_message(ADMIN_ID, msg_admin, reply_markup=markup)
        
        bot.send_message(uid, "⏳ تم إرسال طلبك للإدارة، سيتم التحقق وإضافة الرصيد قريباً.", reply_markup=main_menu(is_admin))
        user_states[uid] = None
        temp_data.pop(uid, None)
        return

    if user_states.get(uid) == "wd_account":
        temp_data[uid]["account"] = text
        user_states[uid] = "wd_amount"
        bot.send_message(uid, "💵 أرسل المبلغ اللي بدك تسحبه:", reply_markup=back_menu())
        return

    if user_states.get(uid) == "wd_amount":
        try: amt = float(text)
        except:
            bot.send_message(uid, "⚠️ أرسل رقم صحيح:", reply_markup=back_menu())
            return
        
        bal, _, _, _ = get_user(uid)
        if amt > bal:
            bot.send_message(uid, f"⚠️ رصيدك {bal} ليرة، ما تكفي", reply_markup=back_menu())
            return

        method = temp_data[uid]["method"]
        account_num = temp_data[uid]["account"]
        
        update_balance(uid, -amt)
        
        conn = db_conn()
        c = conn.cursor()
        c.execute("INSERT INTO pending_withdrawals (user_id, amount, method, account) VALUES (?,?,?,?)", (uid, amt, method, account_num))
        wd_id = c.lastrowid
        conn.commit()
        conn.close()

        net, rate = calc_commission(amt)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ موافقة", callback_data=f"wd_ok_{wd_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"wd_no_{wd_id}"))

        msg_admin = f"💸 طلب سحب جديد\n\n👤 الزبون: {uid}\n📱 الطريقة: {method}\n🔢 حساب الزبون: {account_num}\n💰 المبلغ: {amt}\n📉 العمولة: {rate}%\n✅ الصافي: {net} ليرة"
        bot.send_message(ADMIN_ID, msg_admin, reply_markup=markup)
        
        bot.send_message(uid, f"⏳ تم إرسال طلبك للإدارة.\n💰 المبلغ: {amt}\n📉 العمولة: {rate}%\n✅ الصافي: {net} ليرة\n\nسيتم المعالجة قريباً.", reply_markup=main_menu(is_admin))
        user_states[uid] = None
        temp_data.pop(uid, None)
        return

    if text == "📱 شحن رصيد في البوت":
        user_states[uid] = "dep_method"
        bot.send_message(uid, "📱 اختر طريقة الشحن:", reply_markup=deposit_menu())

    elif text in ("سيرياتيل كاش", "شام كاش", "شام كاش USD") and user_states.get(uid) == "dep_method":
        temp_data[uid] = {"method": text}
        user_states[uid] = "dep_tx"
        
        if text == "شام كاش":
            code = get_setting("sham_cash")
        elif text == "سيرياتيل كاش":
            code = get_setting("syriatel_cash")
        else:
            code = "يرجى التواصل مع الإدارة"
            
        bot.send_message(uid, f"💳 يرجى التحويل إلى هذا الحساب:\n`{code}`\n\nبعد التحويل، أرسل لي **رقم عملية التحويل**:", reply_markup=back_menu(), parse_mode="Markdown")
        return

    if text == "💳 سحب رصيد من البوت":
        bal, _, _, _ = get_user(uid)
        if bal < MIN_WITHDRAWAL:
            bot.send_message(uid, f"⚠️ عذراً، رصيدك الحالي ({bal} ليرة) لا يكفي للسحب. الحد الأدنى للسحب هو {MIN_WITHDRAWAL} ليرة.", reply_markup=main_menu(is_admin))
            return
            
        user_states[uid] = "wd_method"
        bot.send_message(uid, "💳 اختر طريقة السحب:", reply_markup=withdraw_menu())

    elif text in ("سيرياتيل كاش", "شام كاش", "هرم") and user_states.get(uid) == "wd_method":
        temp_data[uid] = {"method": text}
        user_states[uid] = "wd_account"
        bot.send_message(uid, "📝 أرسل عنوان/رقم حسابك اللي بدك تحول عليه:", reply_markup=back_menu())

    elif text == "👤 حسابي":
        acc = get_account(uid)
        if acc: bot.send_message(uid, f"👤 حسابك\n\n👤 المستخدم: {acc[0]}\n🔑 كلمة السر: {acc[1]}", reply_markup=ichancy_menu())
        else: bot.send_message(uid, "ما عندك حساب. اضغط إنشاء حساب:", reply_markup=ichancy_menu())

    elif text == "👤 إنشاء حساب ايشاني":
        user_states[uid] = "reg_username"
        bot.send_message(uid, "👤 أرسل اسم المستخدم (إنجليزي + رقم):", reply_markup=back_menu())

    elif user_states.get(uid) == "reg_username":
        if not text.isascii() or not any(c.isdigit() for c in text):
            bot.send_message(uid, "⚠️ اسم المستخدم لازم إنجليزي وفيه رقم. جرب تاني:", reply_markup=back_menu())
            return
        temp_data[uid] = {"username": text}
        user_states[uid] = "reg_password"
        bot.send_message(uid, "🔐 أرسل كلمة السر (6 خانات على الأقل):", reply_markup=back_menu())

    elif user_states.get(uid) == "reg_password":
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

    elif text == "👥 الإحالات":
        ref_link = f"https://t.me/{(bot.get_me()).username}?start={uid}"
        conn_users = get_all_users()
        total = len([u for u in conn_users if get_user(u)[3] == uid])
        active = len([u for u in conn_users if get_user(u)[3] == uid and get_user(u)[1] > 0])
        net = sum(max(0, get_user(u)[1] - get_user(u)[2]) for u in conn_users if get_user(u)[3] == uid)
        earnings = net * REFERRAL_PROFIT_SHARE if active >= REFERRAL_MIN_ACTIVE else 0
        msg = f"👥 الإحالات\n\n🔗 رابطك: {ref_link}\n\n📊 إجمالي: {total}\n✅ نشطة: {active}\n💰 صافي خسارة: {net}\n🎁 أرباحك (5%): {earnings}\n\n⚠️ شرط: 3 إحالات نشطة على الأقل"
        bot.send_message(uid, msg, reply_markup=back_menu())

    elif text == "📊 السجلات":
        bot.send_message(uid, "📊 سجلاتك:\n\n(سيتم إضافة السجلات قريباً)", reply_markup=back_menu())

    elif text == "🎧 إرسال رسالة للدعم":
        user_states[uid] = "support"
        bot.send_message(uid, "🎧 أرسل رسالتك:", reply_markup=back_menu())

    elif text == "🌐 ايشاني":
        mk = InlineKeyboardMarkup()
        mk.add(InlineKeyboardButton("🌐 فتح الموقع", url="https://agents.ichancy.com"))
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

    elif text == "👥 إحصائيات الأعضاء" and is_admin:
        all_u = get_all_users()
        bot.send_message(uid, f"👥 عدد الأعضاء: {len(all_u)}", reply_markup=admin_menu())

    elif user_states.get(uid) == "broadcast" and is_admin:
        for u in get_all_users():
            try: bot.send_message(u, text)
            except: pass
        user_states[uid] = None
        bot.send_message(uid, "✅ تمت الإذاعة", reply_markup=admin_menu())

    elif user_states.get(uid) == "sham_update" and is_admin:
        set_setting("sham_cash", text)
        user_states[uid] = None
        msg = f"✅ تم تحديث شام كاش: {text}"
        bot.send_message(uid, msg, reply_markup=admin_menu())

    elif user_states.get(uid) == "syriatel_update" and is_admin:
        set_setting("syriatel_cash", text)
        user_states[uid] = None
        msg = f"✅ تم تحديث سيرياتيل: {text}"
        bot.send_message(uid, msg, reply_markup=admin_menu())

    elif user_states.get(uid) == "support":
        bot.send_message(ADMIN_ID, f"🎧 رسالة دعم من {uid}:\n\n{text}")
        user_states[uid] = None
        bot.send_message(uid, "✅ تم إرسال رسالتك", reply_markup=main_menu(is_admin))

# ==================== Webhook ====================
@app.route("/", methods=["GET"])
def index():
return "Bot is running!", 200

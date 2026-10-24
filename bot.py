import os
import random
import sqlite3
import requests
from datetime import date
from flask import Flask, request
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '8734379872:AAFpX_ZqN0_mdJhZW2gj1yiNYJDIAVUqp18'
ADMIN_ID = 7753870725
MIN_WITHDRAWAL = 500
WHEEL_DAILY_LIMIT = 750
ICHANCY_URL = "https://www.ichancy.com"

# كود الوكالة السري (مخفي تماماً عن اللاعبين)
AGENT_CODE = "2826132-odai1@agents.nps"

# إعدادات قناة الاشتراك الإجباري (ضع معرف قناتك هنا مثل @YourChannel)
CHANNEL_USERNAME = "@YourChannel"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY, 
                        first_name TEXT, 
                        daily_deposit REAL DEFAULT 0,
                        last_deposit_date TEXT,
                        last_spin_date TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                        user_id INTEGER,
                        username TEXT,
                        password TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance', 'off')")
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('sham_cash', 'غير محدد حالياً')")
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('syriatel_cash', 'غير محدد حالياً')")
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('custom_terms', 'شروط وأحكام وكالة iChancy:\n1. يتم خصم الرصيد تلقائياً من حساب iChancy عند طلب السحب.\n2. تحويل المبلغ المسحوب إلى كاش اللاعب (شام كاش أو سيريتل كاش).\n3. الحد الأدنى للسحب هو 500 ليرة.')")
    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else ""

def set_setting(key, value):
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def add_user(user_id, first_name):
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))
    conn.commit()
    conn.close()

def check_username_exists(username):
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM accounts WHERE username=?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_player_account(user_id, username, password):
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO accounts VALUES (?, ?, ?)", (user_id, username, password))
    conn.commit()
    conn.close()

def get_user_daily_data(user_id):
    today = str(date.today())
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT daily_deposit, last_deposit_date, last_spin_date FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return 0, False
    daily_dep, last_dep_date, last_spin_date = row
    if last_dep_date != today:
        daily_dep = 0
    has_spun_today = (last_spin_date == today)
    return daily_dep, has_spun_today

def add_user_deposit(user_id, amount):
    today = str(date.today())
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT last_deposit_date, daily_deposit FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] == today:
        new_amount = row[1] + amount
    else:
        new_amount = amount
    cursor.execute("UPDATE users SET daily_deposit = ?, last_deposit_date = ? WHERE user_id=?", (new_amount, today, user_id))
    conn.commit()
    conn.close()

def set_user_spun_today(user_id):
    today = str(date.today())
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_spin_date = ? WHERE user_id=?", (today, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_data.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

# دالة التحقق من الاشتراك الإجباري في القناة
def check_user_subscription(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        print(f"Subscription check error: {e}")
    return False

# دوال ربط الكاشيرة والموقع (API Integration)
def ichancy_api_create_account(username, password):
    # ضع هنا رابط واجهة الـ API والرمز الخاص بكاشيرة وكالتك عندما تتوفر لديك
    api_endpoint = "https://api.ichancy.com/v1/create_account"
    payload = {
        "agent_code": AGENT_CODE,
        "username": username,
        "password": password
    }
    try:
        # response = requests.post(api_endpoint, json=payload, timeout=10)
        # return response.json().get("success", True)
        return True # تفعيل افتراضي ريثما تربط بيانات الـ API الفعلية
    except:
        return True

def ichancy_api_withdraw(username, amount):
    api_endpoint = "https://api.ichancy.com/v1/withdraw"
    payload = {
        "agent_code": AGENT_CODE,
        "username": username,
        "amount": amount
    }
    try:
        # response = requests.post(api_endpoint, json=payload, timeout=10)
        # return response.json().get("success", True)
        return True # تفعيل افتراضي ريثما تربط بيانات الـ API الفعلية
    except:
        return True

def main_menu(is_admin=False):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("👤 إنشاء حساب"),
        KeyboardButton("💳 شحن الرصيد"),
        KeyboardButton("💸 سحب الرصيد"),
        KeyboardButton("🎰 عجلة الفرصة"),
        KeyboardButton("🎁 قسم الهدايا"),
        KeyboardButton("👥 نظام الإحالات"),
        KeyboardButton("📊 حسابي والمعلومات"),
        KeyboardButton("📜 شروط الاستخدام"),
        KeyboardButton("🎧 خدمة الدعم"),
        KeyboardButton("🗑️ طلب حذف الحساب")
    )
    if is_admin:
        markup.add(KeyboardButton("⚙️ لوحة تحكم الآدمن"))
    return markup

def subscription_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 اضغط هنا للانضمام للقناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
    markup.add(InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_sub"))
    return markup

def deposit_methods_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("📱 شحن شام كاش"),
        KeyboardButton("📱 شحن سيريتل كاش"),
        KeyboardButton("🔙 رجوع للقائمة الرئيسية")
    )
    return markup

def withdraw_methods_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("💸 سحب عبر شام كاش"),
        KeyboardButton("💸 سحب عبر سيريتل كاش"),
        KeyboardButton("🔙 رجوع للقائمة الرئيسية")
    )
    return markup

def back_menu():
    markup = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(KeyboardButton("🔙 رجوع للقائمة الرئيسية"))
    return markup

def admin_panel_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m_status = "إيقاف الصيانة 🔴" if get_setting('maintenance') == 'on' else "تشغيل الصيانة 🟢"
    markup.add(
        KeyboardButton(f"🛠️ {m_status}"),
        KeyboardButton("📢 إرسال إذاعة للجميع"),
        KeyboardButton("📱 تغيير كود الشام كاش"),
        KeyboardButton("📱 تغيير كود سيريتل كاش"),
        KeyboardButton("👥 عدد الأعضاء المسجلين"),
        KeyboardButton("🔙 رجوع للقائمة الرئيسية")
    )
    return markup

def wheel_inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎡 تدوير العجلة الآن!", callback_data="spin_wheel"))
    return markup

@app.route('/', methods=['GET'])
def index():
    return 'iChancy Bot is Online!', 200

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

admin_rejection_states = {}
user_registration_temp = {}
deposit_temp = {}
withdraw_temp = {}
user_states = {}

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.message.chat.id
    is_admin = (user_id == ADMIN_ID)

    if call.data == "check_sub":
        if check_user_subscription(user_id):
            bot.answer_callback_query(call.id, text="✅ تم التحقق من اشتراكك بنجاح!", show_alert=True)
            bot.delete_message(user_id, call.message.message_id)
            bot.send_message(user_id, "أهلاً بك مجدداً في بوت وكالة iChancy الرسمية! اختر من القائمة:", reply_markup=main_menu(is_admin))
        else:
            bot.answer_callback_query(call.id, text="⚠️ لم تقم بالانضمام للقناة بعد!", show_alert=True)
        return

    if call.data == "spin_wheel":
        daily_dep, has_spun = get_user_daily_data(user_id)
        if has_spun and not is_admin:
            bot.answer_callback_query(call.id, text="⚠️ لقد استخدمت فرصة اليوم!", show_alert=True)
            return
        if daily_dep < WHEEL_DAILY_LIMIT and not is_admin:
            bot.answer_callback_query(call.id, text="⚠️ لم تحقق شرط الشحن اليومي بعد!", show_alert=True)
            return
        set_user_spun_today(user_id)
        prizes = [
            ("❌ حظاً أفر في المرة القادمة!", 50),
            ("🔄 مبروك! لفة مجانية جديدة!", 30),
            ("💵 مبروك! ربحت 50 ليرة جديدة!", 20)
        ]
        prize_pool = [p[0] for p in prizes for _ in range(p[1])]
        selected_prize = random.choice(prize_pool)
        bot.answer_callback_query(call.id, text="🔄 جاري التدوير...")
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text="🌀 العجلة تدور الآن...")
        bot.send_message(user_id, f"🎯 النتيجة:\n\n{selected_prize}", reply_markup=back_menu())

    elif call.data.startswith("approve_"):
        data_parts = call.data.split("_")
        target_user = int(data_parts[1])
        req_type = data_parts[2]
        bot.answer_callback_query(call.id, text="✅ تمت الموافقة وتأكيد العملية.")
        if req_type == "dep":
            add_user_deposit(target_user, 750)
            bot.send_message(target_user, "✅ تم الموافقة على طلب الشحن وتحديث رصيدك.")
        else:
            bot.send_message(target_user, "✅ تم خصم الرصيد تلقائياً من حساب iChancy وتحويل المبلغ لكاش الخاص بك بنجاح.")
        bot.edit_message_text(f"{call.message.text}\n\n🟢 الحالة: تم الخصم والتنفيذ المباشر", chat_id=ADMIN_ID, message_id=call.message.message_id)

    elif call.data.startswith("reject_"):
        data_parts = call.data.split("_")
        target_user = int(data_parts[1])
        bot.answer_callback_query(call.id, text="❌ أرسل سبب الرفض.")
        admin_rejection_states[ADMIN_ID] = {'target_user': target_user, 'msg_id': call.message.message_id, 'orig_text': call.message.text}
        bot.send_message(ADMIN_ID, f"أرسل سبب الرفض للمستخدم {target_user}:")

@bot.message_handler(commands=['start', 'admin'])
def send_welcome(message):
    user_id = message.chat.id
    add_user(user_id, message.from_user.first_name)
    user_states[user_id] = None
    is_admin = (user_id == ADMIN_ID)
    
    if get_setting('maintenance') == 'on' and not is_admin:
        bot.send_message(user_id, "⚠️ البوت في وضع الصيانة.")
        return

    if not check_user_subscription(user_id):
        sub_msg = f"🚀 لاستخدام هذا البوت، يجب عليك أولاً الانضمام إلى قناتنا الرسمية:\n\n{CHANNEL_USERNAME}"
        bot.send_message(user_id, sub_msg, reply_markup=subscription_keyboard())
        return

    if is_admin:
        bot.send_message(user_id, "👑 أهلاً بك يا مدير الوكالة!", reply_markup=main_menu(True))
        return
    bot.send_message(user_id, "مرحباً بك في بوت وكالة iChancy الرسمية!", reply_markup=main_menu(False))

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo'])
def handle_messages(message):
    user_id = message.chat.id
    text = message.text if message.text else ""
    is_admin = (user_id == ADMIN_ID)

    if not check_user_subscription(user_id):
        sub_msg = f"🚀 لاستخدام هذا البوت، يجب عليك أولاً الانضمام إلى قناتنا الرسمية:\n\n{CHANNEL_USERNAME}"
        bot.send_message(user_id, sub_msg, reply_markup=subscription_keyboard())
        return

    if is_admin and ADMIN_ID in admin_rejection_states:
        info = admin_rejection_states.pop(ADMIN_ID)
        target_user = info['target_user']
        reason = text
        bot.send_message(target_user, f"❌ عذراً، تم رفض طلبك.\nالسبب: {reason}")
        bot.edit_message_text(f"{info['orig_text']}\n\n🔴 الحالة: مرفوض\nالسبب: {reason}", chat_id=ADMIN_ID, message_id=info['msg_id'])
        bot.send_message(ADMIN_ID, "✅ تم الإرسال بنجاح.", reply_markup=admin_panel_menu())
        return

    if get_setting('maintenance') == 'on' and not is_admin:
        bot.send_message(user_id, "⚠️ البوت مغلق للصيانة.")
        return

    main_buttons = ["👤 إنشاء حساب", "💳 شحن الرصيد", "💸 سحب الرصيد", "🎰 عجلة الفرصة", "🎁 قسم الهدايا", "👥 نظام الإحالات", "📊 حسابي والمعلومات", "📜 شروط الاستخدام", "🎧 خدمة الدعم", "🗑️ طلب حذف الحساب", "⚙️ لوحة تحكم الآدمن", "🔙 رجوع للقائمة الرئيسية", "📱 شحن شام كاش", "📱 شحن سيريتل كاش", "💸 سحب عبر شام كاش", "💸 سحب عبر سيريتل كاش"]
    if text in main_buttons:
        user_states[user_id] = None

    state = user_states.get(user_id)

    if state == 'awaiting_username':
        if check_username_exists(text):
            bot.send_message(user_id, "⚠️ اسم المستخدم مستخدم مسبقاً!", reply_markup=back_menu())
            return
        user_registration_temp[user_id] = {'username': text}
        user_states[user_id] = 'awaiting_password'
        bot.send_message(user_id, "🔐 أرسل كلمة المرور (6 خانات على الأقل):", reply_markup=back_menu())
        return

    if state == 'awaiting_password':
        if len(text) < 6:
            bot.send_message(user_id, "⚠️ كلمة المرور قصيرة جداً!")
            return
        username = user_registration_temp.get(user_id, {}).get('username', 'غير محدد')
        password = text
        user_states[user_id] = None
        user_registration_temp.pop(user_id, None)
        
        # إنشاء الحساب في كاشيرة iChancy آلياً عبر الـ API
        ichancy_api_create_account(username, password)
        
        save_player_account(user_id, username, password)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌐 الدخول الفوري إلى iChancy", url=ICHANCY_URL))
        
        success_msg = f"✅ تم إنشاء حسابك بنجاح ونزوله في الكاشيرة تلقائياً! 🎉\n\n• اسم المستخدم: `{username}`\n• كلمة المرور: `{password}`\n\nاضغط على الزر أدناه للدخول إلى حسابك مباشرة:"
        bot.send_message(user_id, success_msg, reply_markup=markup, parse_mode="Markdown")
        bot.send_message(ADMIN_ID, f"👤 حساب جديد مضاف للكاشيرة تلقائياً:\n• اليوزر: {username}\n• الباسورد: {password}\n• ID: {user_id}")
        return

    if state == 'awaiting_dep_tx_id':
        deposit_temp[user_id]['tx_id'] = text
        user_states[user_id] = 'awaiting_dep_amount'
        bot.send_message(user_id, "💵 الآن أرسل قيمة المبلغ المحول بالليرة:", reply_markup=back_menu())
        return

    if state == 'awaiting_dep_amount':
        method = deposit_temp.get(user_id, {}).get('method', 'غير محدد')
        tx_id = deposit_temp.get(user_id, {}).get('tx_id', 'غير محدد')
        amount = text
        user_states[user_id] = None
        deposit_temp.pop(user_id, None)
        bot.send_message(user_id, "⏳ الطلب قيد المراجعة لدى الإدارة.", reply_markup=main_menu(is_admin))
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ قبول الشحن", callback_data=f"approve_{user_id}_dep"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}_dep"))
        admin_msg = f"📥 طلب شحن جديد ({method}):\n• المستخدم: {message.from_user.first_name} ({user_id})\n• رقم العملية: {tx_id}\n• المبلغ: {amount} ليرة"
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
        return

    if state == 'awaiting_ichancy_username':
        withdraw_temp[user_id] = {'ichancy_username': text}
        user_states[user_id] = 'awaiting_ichancy_amount'
        bot.send_message(user_id, f"💵 أدخل المبلغ المراد سحبه من حساب iChancy (الحد الأدنى {MIN_WITHDRAWAL} ليرة):", reply_markup=back_menu())
        return

    if state == 'awaiting_ichancy_amount':
        withdraw_temp[user_id]['amount'] = text
        user_states[user_id] = None
        bot.send_message(user_id, "💳 اختر طريقة استلام الأرباح المحولة:", reply_markup=withdraw_methods_menu())
        return

    if state == 'awaiting_payout_code':
        payout_code = text
        w_data = withdraw_temp.get(user_id, {})
        ichancy_user = w_data.get('ichancy_username', 'غير محدد')
        amount = w_data.get('amount', 'غير محدد')
        method = w_data.get('method', 'غير محدد')
        
        user_states[user_id] = None
        withdraw_temp.pop(user_id, None)

        # الخصم التلقائي من حساب iChancy عبر الـ API
        ichancy_api_withdraw(ichancy_user, amount)

        bot.send_message(user_id, "⏳ جاري خصم الرصيد من حسابك في iChancy وتحويل المبلغ لعنوان الكاش الخاص بك...", reply_markup=main_menu(is_admin))
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ تأكيد السحب والخصم الآلي", callback_data=f"approve_{user_id}_with"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}_with"))
        
        admin_msg = (
            f"💸 **طلب سحب رصيد مفصل (تلقائي):**\n\n"
            f"1️⃣ **حساب iChancy المسحوب منه:** `{ichancy_user}`\n"
            f"2️⃣ **المبلغ المطلوب خصمه:** {amount} ليرة\n"
            f"3️⃣ **طريقة التحويل:** {method}\n"
            f"4️⃣ **كود الكاش للاستلام:** `{payout_code}`\n\n"
            f"• **المستخدم:** {message.from_user.first_name} (`{user_id}`)"
        )
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup, parse_mode="Markdown")
        return

    if state == 'awaiting_broadcast' and is_admin:
        users = get_all_users()
        count = 0
        for u in users:
            try:
                if message.photo:
                    bot.send_photo(u, message.photo[-1].file_id, caption=message.caption)
                else:
                    bot.send_message(u, text)
                count += 1
            except:
                pass
        bot.send_message(user_id, f"✅ تم الإرسال إلى {count} عضو.", reply_markup=admin_panel_menu())
        user_states[user_id] = None
        return

    if state == 'awaiting_sham' and is_admin:
        set_setting('sham_cash', text)
        bot.send_message(user_id, f"✅ تم تحديث شام كاش:\n{text}", reply_markup=admin_panel_menu())
        user_states[user_id] = None
        return

    if state == 'awaiting_syriatel' and is_admin:
        set_setting('syriatel_cash', text)
        bot.send_message(u

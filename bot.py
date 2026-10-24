import os
import random
import sqlite3
from datetime import date
from flask import Flask, request
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '8734379872:AAFpX_ZqN0_mdJhZW2gj1yiNYJDIAVUqp18'
ADMIN_ID = 2826132
MIN_WITHDRAWAL = 500
WHEEL_DAILY_LIMIT = 750
ICHANCY_URL = "https://www.ichancy.com"

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
    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('custom_terms', 'شروط وأحكام وكالة iChancy:\n1. الحد الأدنى للسحب هو 500 ليرة.\n2. فتح عجلة الفرصة يتطلب شحن بقيمة 750 ليرة جديدة خلال اليوم، وتمنح لفة واحدة يومياً.\n3. كلمة المرور للحساب يجب أن لا تقل عن 6 خانات.')")
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
user_states = {}

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.message.chat.id
    is_admin = (user_id == ADMIN_ID)

    if call.data == "spin_wheel":
        daily_dep, has_spun = get_user_daily_data(user_id)
        if has_spun and not is_admin:
            bot.answer_callback_query(call.id, text="⚠️ لقد استخدمت فرصة اليوم! انتظر لغدٍ بعد الشحن.", show_alert=True)
            return
        if daily_dep < WHEEL_DAILY_LIMIT and not is_admin:
            bot.answer_callback_query(call.id, text="⚠️ لم تحقق شرط الشحن اليومي (750 ليرة) بعد!", show_alert=True)
            return
        set_user_spun_today(user_id)
        prizes = [
            ("❌ حظاً أفر في المرة القادمة، جرب مجدداً غداً!", 50),
            ("🔄 مبروك! حصلت على لفة مجانية جديدة!", 30),
            ("💵 مبروك! ربحت 50 ليرة جديدة!", 20)
        ]
        prize_pool = [p[0] for p in prizes for _ in range(p[1])]
        selected_prize = random.choice(prize_pool)
        bot.answer_callback_query(call.id, text="🔄 جاري تدوير العجلة...")
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text="🌀 العجلة تدور الآن...\n\n🎰 [ 🎡 🎡 🎡 ]")
        bot.send_message(user_id, f"🎯 نتيجة عجلة الفرصة اليومية:\n\n{selected_prize}\n\nتواصل مع الدعم لتثبيت الجائزة إن وجدت!", reply_markup=back_menu())

    elif call.data.startswith("approve_"):
        data_parts = call.data.split("_")
        target_user = int(data_parts[1])
        req_type = data_parts[2]
        bot.answer_callback_query(call.id, text="✅ تمت الموافقة بنجاح.")
        if req_type == "dep":
            add_user_deposit(target_user, 750)
            bot.send_message(target_user, "✅ مبروك! تم الموافقة على طلب الشحن وتحديث رصيدك وتفعيل عجلة الفرصة لليوم.")
        else:
            bot.send_message(target_user, "✅ مبروك! تم الموافقة على طلب السحب وإرسال المبلغ بنجاح.")
        bot.edit_message_text(f"{call.message.text}\n\n🟢 الحالة: تم القبول والتنفيذ", chat_id=ADMIN_ID, message_id=call.message.message_id)

    elif call.data.startswith("reject_"):
        data_parts = call.data.split("_")
        target_user = int(data_parts[1])
        bot.answer_callback_query(call.id, text="❌ أرسل سبب الرفض.")
        admin_rejection_states[ADMIN_ID] = {'target_user': target_user, 'msg_id': call.message.message_id, 'orig_text': call.message.text}
        bot.send_message(ADMIN_ID, f"أرسل الآن سبب الرفض للمستخدم {target_user}:")

@bot.message_handler(commands=['start', 'admin'])
def send_welcome(message):
    user_id = message.chat.id
    add_user(user_id, message.from_user.first_name)
    user_states[user_id] = None
    is_admin = (user_id == ADMIN_ID)
    if get_setting('maintenance') == 'on' and not is_admin:
        bot.send_message(user_id, "⚠️ البوت حالياً في وضع الصيانة للتحديث.\nيرجى المحاولة لاحقاً!")
        return
    if is_admin:
        bot.send_message(user_id, "👑 أهلاً بك يا مدير الوكالة!\nحسابك مفعّل كآدمن بالكامل.", reply_markup=main_menu(True))
        return
    welcome_text = "مرحباً بك في بوت إدارة وكالة iChancy الرسمية! 🎰\n\nيرجى اختيار إحدى الخدمات من القائمة أدناه:"
    bot.send_message(user_id, welcome_text, reply_markup=main_menu(False))

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo'])
def handle_messages(message):
    user_id = message.chat.id
    text = message.text if message.text else ""
    is_admin = (user_id == ADMIN_ID)

    if is_admin and ADMIN_ID in admin_rejection_states:
        info = admin_rejection_states.pop(ADMIN_ID)
        target_user = info['target_user']
        reason = text
        bot.send_message(target_user, f"❌ عذراً، تم رفض طلبك من قبل الإدارة.\n\n📌 السبب: {reason}")
        bot.edit_message_text(f"{info['orig_text']}\n\n🔴 الحالة: تم الرفض\n📝 السبب: {reason}", chat_id=ADMIN_ID, message_id=info['msg_id'])
        bot.send_message(ADMIN_ID, "✅ تم إرسال سبب الرفض للمستخدم بنجاح.", reply_markup=admin_panel_menu())
        return

    if get_setting('maintenance') == 'on' and not is_admin:
        bot.send_message(user_id, "⚠️ البوت مغلق مؤقتاً للصيانة. سنعود قريباً!")
        return

    main_buttons = ["👤 إنشاء حساب", "💳 شحن الرصيد", "💸 سحب الرصيد", "🎰 عجلة الفرصة", "🎁 قسم الهدايا", "👥 نظام الإحالات", "📊 حسابي والمعلومات", "📜 شروط الاستخدام", "🎧 خدمة الدعم", "🗑️ طلب حذف الحساب", "⚙️ لوحة تحكم الآدمن", "🔙 رجوع للقائمة الرئيسية"]
    if text in main_buttons:
        user_states[user_id] = None

    state = user_states.get(user_id)

    if state == 'awaiting_username':
        if check_username_exists(text):
            bot.send_message(user_id, "⚠️ اسم المستخدم هذا موجود مسبقاً!\nيرجى إرسال اسم مستخدم (Username) آخر:", reply_markup=back_menu())
            return
        user_registration_temp[user_id] = {'username': text}
        user_states[user_id] = 'awaiting_password'
        bot.send_message(user_id, "🔐 الآن أرسل كلمة المرور المطلوبة لحسابك (يجب ألا تقل عن 6 خانات):", reply_markup=back_menu())
        return

    if state == 'awaiting_password':
        if len(text) < 6:
            bot.send_message(user_id, "⚠️ كلمة المرور قصيرة جداً!\nيرجى كتابة كلمة مرور تتكون من 6 خانات أو أكثر:")
            return
        username = user_registration_temp.get(user_id, {}).get('username', 'غير محدد')
        password = text
        user_states[user_id] = None
        user_registration_temp.pop(user_id, None)
        save_player_account(user_id, username, password)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🌐 الدخول الفوري إلى iChancy", url=ICHANCY_URL))
        success_msg = f"✅ تم إنشاء حسابك بنجاح تام! 🎉\n\n• اسم المستخدم: {username}\n• كلمة المرور: {password}\n\nيمكنك الآن الضغط على الزر أدناه ودخول موقع iChancy بحسابك الجديد مباشرة:"
        bot.send_message(user_id, success_msg, reply_markup=markup)
        bot.send_message(ADMIN_ID, f"👤 تم تسجيل حساب جديد بالبوت:\n• اللاعب: {message.from_user.first_name}\n• اليوزر: {username}\n• الباسورد: {password}\n• ID: {user_id}")
        return

    if state == 'deposit_req':
        bot.send_message(user_id, "⏳ تم استلام طلب الشحن بنجاح وهو قيد المراجعة لدى الإدارة.", reply_markup=main_menu(is_admin))
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ قبول الشحن", callback_data=f"approve_{user_id}_dep"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}_dep"))
        bot.send_message(ADMIN_ID, f"📥 طلب شحن جديد:\n• المستخدم: {message.from_user.first_name} ({user_id})\n• التفاصيل:\n{text}", reply_markup=markup)
        user_states[user_id] = None
        return

    if state == 'withdraw_req':
        bot.send_message(user_id, "⏳ تم استلام طلب السحب بنجاح وهو قيد المراجعة لدى الإدارة.", reply_markup=main_menu(is_admin))
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ قبول السحب", callback_data=f"approve_{user_id}_with"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}_with"))
        bot.send_message(ADMIN_ID, f"💸 طلب سحب جديد:\n• المستخدم: {message.from_user.first_name} ({user_id})\n• التفاصيل:\n{text}", reply_markup=markup)
        user_states[user_id] = None
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
        bot.send_message(user_id, f"✅ تم إرسال الإذاعة بنجاح إلى {count} عضو.", reply_markup=admin_panel_menu())
        user_states[user_id] = None
        return

    if state == 'awaiting_sham' and is_admin:
        set_setting('sham_cash', text)
        bot.send_message(user_id, f"✅ تم تحديث كود الشام كاش إلى:\n{text}", reply_markup=admin_panel_menu())
        user_states[user_id] = None
        return

    if state == 'awaiting_syriatel' and is_admin:
        set_setting('syriatel_cash', text)
        bot.send_message(user_id, f"✅ تم تحديث كود سيريتل كاش إلى:\n{text}", reply_markup=admin_panel_menu())
        user_states[user_id] = None
        return

    if text == "⚙️ لوحة تحكم الآدمن" and is_admin:
        bot.send_message(user_id, "أهلاً بك في لوحة الإدارة:", reply_markup=admin_panel_menu())
        return
    if "تشغيل الصيانة" in text and is_admin:
        set_setting('maintenance', 'on')
        bot.send_message(user_id, "🛑 تم تفعيل وضع الصيانة بنجاح.", reply_markup=admin_panel_menu())
        return
    if "إيقاف الصيانة" in text and is_admin:
        set_setting('maintenance', 'off')
        bot.send_message(user_id, "🟢 تم إيقاف الصيانة وعمل البوت طبيعياً.", reply_markup=admin_panel_menu())
        return
    if text == "📢 إرسال إذاعة للجميع" and is_admin:
        user_states[user_id] = 'awaiting_broadcast'
        bot.send_message(user_id, "أرسل النص أو الصورة مع التعليق لإذاعتها للجميع الآن:")
        return
    if text == "📱 تغيير كود الشام كاش" and is_admin:
        user_states[user_id] = 'awaiting_sham'
        bot.send_message(user_id, f"الكود الحالي لشام كاش: {get_setting('sham_cash')}\n\nأرسل الكود الجديد:")
        return
    if text == "📱 تغيير كود سيريتل كاش" and is_admin:
        user_states[user_id] = 'awaiting_syriatel'
        bot.send_message(user_id, f"الكود الحالي لسيريتل كاش: {get_setting('syriatel_cash')}\n\nأرسل الكود الجديد:")
        return
    if text == "👥 عدد الأعضاء المسجلين" and is_admin:
        total = len(get_all_users())
        bot.send_message(user_id, f"📊 إجمالي عدد المشتركين: {total} عضو")
        return

    if text == "🔙 رجوع للقائمة الرئيسية":
        user_states[user_id] = None
        user_registration_temp.pop(user_id, None)
        bot.send_message(user_id, "تم العودة للقائمة الرئيسية:", reply_markup=main_menu(is_admin))
    elif text == "👤 إنشاء حساب":
        user_states[user_id] = 'awaiting_username'
        bot.send_message(user_id, "👤 لإنشاء حساب جديد، يرجى إرسال اسم المستخدم (Username) المطلوب:", reply_markup=back_menu())
    elif text == "💳 شحن الرصيد":
        user_states[user_id] = 'deposit_req'
        sham = get_setting('sham_cash')
        syriatel = get_setting('syriatel_cash')
        msg = f"💳 طرق شحن الرصيد المتاحة:\n\n• الشام كاش: {sham}\n• سيريتل كاش: {syriatel}\n\nأرسل اسم حسابك، المبلغ المحول، ورقم الإشعار هنا للمراجعة:"
        bot.send_message(user_id, msg, reply_markup=back_menu())
    elif text == "💸 سحب الرصيد":
        user_states[user_id] = 'withdraw_req'
        msg = f"⚠️ شروط سحب الأرباح:\n• الحد الأدنى للسحب هو {MIN_WITHDRAWAL} ليرة.\n\nأرسل اسم حسابك، المبلغ المراد سحبه، ورقم الكاش الخاص بك:"
        bot.send_message(user_id, msg, reply_markup=back_menu())
    elif text == "🎰 عجلة الفرصة":
        daily_dep, has_spun = get_user_daily_data(user_id)
        if has_spun and not is_admin:
            bot.send_message(user_id, "🛑 لقد استخدمت فرصة اليوم بالفعل!\nيرجى العودة غداً بعد الشحن للحصول على فرصة جديدة.", reply_markup=back_menu())
        elif daily_dep < WHEEL_DAILY_LIMIT and not is_admin:
            msg = f"🔒 عجلة الفرصة مقفلة اليوم!\n\n• الشرط: شحن رصيد بقيمة 750 ليرة جديدة (75,000 قديمة) على الأقل خلال اليوم للحصول على دورة واحدة.\n• مجموع شحناتك اليوم: {daily_dep} ليرة.\n\nقم بشحن رصيدك عبر زر (شحن الرصيد) لتفتح معك العجلة فوراً!"
            bot.send_message(user_id, msg, reply_markup=back_menu())
        else:
            wheel_text = "🎰 أهلاً بك في عجلة الفرصة اليومية! 🎡\n\nلك فرصة واحدة اليوم! اضغط على الزر أدناه للتدوير:"
            bot.send_message(user_id, wheel_text, reply_markup=wheel_inline_keyboard())
    elif text == "🎁 قسم الهدايا":
        bot.send_message(user_id, "🎁 قسم هدايا الوكالة والعروض اليومية.", reply_markup=back_menu())
    elif text == "👥 نظام الإحالات":
        bot.send_message(user_id, "👥 شارك رابط البوت مع أصدقائك للحصول على مكافآت.", reply_markup=back_menu())
    elif text == "📊 حسابي والمعلومات":
        daily_dep, has_spun = get_user_daily_data(user_id)
        spin_st = "تم استخدامها اليوم 🔴" if has_spun else ("متاحة لليوم 🟢" if daily_dep >= WHEEL_DAILY_LIMIT or is_admin else "مقفلة 🔒")
        info = f"👤 معلومات حسابك:\n• الاسم: {message.from_user.first_name}\n• الـ ID: {user_id}\n• شحنك اليومي: {daily_dep} ليرة\n• حالة العجلة: {spin_st}\n• أدنى حد للسحب: {MIN_WITHDRAWAL} ليرة"
        bot.send_message(user_id, info, reply_markup=back_menu())
    elif text == "📜 شروط الاستخدام":
        terms = get_setting('custom_terms')
        bot.send_message(user_id, terms, reply_markup=back_menu())
    elif text == "🎧 خدمة الدعم":
        bot.send_message(user_id, "🎧 أرسل استفسارك وسيقوم الآدمن بالرد عليك.", reply_markup=back_menu())
    elif text == "🗑️ طلب حذف الحساب":
        bot.send_message(user_id, "🗑️ أرسل اسم حسابك لتأكيد طلب الحذف لدى الإدارة.", reply_markup=back_menu())
    else:
        bot.send_message(user_id, "اختر إحدى الخدمات من القائمة أدناه:", reply_markup=main_menu(is_admin))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    

import os
import time
import random
import requests
import telebot
from flask import Flask, request

API_TOKEN = '8734379872:AAFpX_ZqN0_mdJhZW2gj1yiNYJDIAVUqp18' 
AGENT_ID = "2826132-odai1@agents.nps"
ICHANCY_API_URL = "https://agents.ichancy.com/api/create_player"

SETTINGS = {
    "maintenance": False,
    "sham_cash": "يرجى التواصل مع الإدارة",
    "syriatel_cash": "يرجى التواصل مع الإدارة",
    "referral_url": "https://t.me/odairobertbot?start=",
    "deposit_bonus_active": False,
    "deposit_bonus_percentage": 10,
    "support_link": "https://t.me/odairobertbot"
}

CUSTOM_DEPOSIT_METHODS = {
    "شام كاش (Sham Cash)": "يرجى ضبط العنوان من الإدارة",
    "سيرياتل كاش (Syriatel Cash)": "يرجى ضبط الرقم من الإدارة"
}

CUSTOM_WITHDRAW_METHODS = [
    "شام كاش",
    "سيرياتل كاش"
]

MIN_DEPOSIT = 250        
MIN_WITHDRAW = 500       

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

USER_BALANCES = {}
USER_IDS = set()
ADMIN_IDS = set()
REGISTERED_USERNAMES = set()
TEMP_USER_DATA = {}
TEMP_DEPOSIT_DATA = {}
PENDING_DEPOSITS = {}
ADMIN_STATES = {}

def check_maintenance(message):
    if SETTINGS["maintenance"] and message.chat.id not in ADMIN_IDS:
        bot.send_message(
            message.chat.id, 
            "⚠️ **البوت قيد الصيانة حالياً!**\n\nنعمل على تحديث وتطوير النظام، يرجى المحاولة لاحقاً.",
            parse_mode="Markdown"
        )
        return True
    return False

@app.route(f'/{API_TOKEN}', methods=['POST'])
def webhook():
    try:
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"Error: {e}")
    return "OK", 200

@app.route('/')
def index():
    return "Bot is running perfectly!", 200

@app.route('/wheel')
def wheel_page():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>عجلة الفرصة</title>
        <style>
            body { background: #0f172a; color: #fff; font-family: Tahoma, sans-serif; text-align: center; padding: 20px; }
            h2 { color: #facc15; }
            .wheel-container { position: relative; width: 300px; height: 300px; margin: 30px auto; }
            canvas { width: 100%; height: 100%; border-radius: 50%; border: 6px solid #facc15; transition: transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99); }
            .pin { position: absolute; top: -15px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 12px solid transparent; border-right: 12px solid transparent; border-top: 24px solid #ef4444; z-index: 10; }
            button { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: none; padding: 12px 35px; font-size: 18px; font-weight: bold; border-radius: 30px; cursor: pointer; margin-top: 20px; }
            #result { margin-top: 20px; font-size: 20px; font-weight: bold; color: #4ade80; }
        </style>
    </head>
    <body>
        <h2>⭐ عجلة الفرصة الكبرى ⭐</h2>
        <div class="wheel-container">
            <div class="pin"></div>
            <canvas id="wheelCanvas" width="300" height="300"></canvas>
        </div>
        <button id="spinBtn" onclick="spinWheel()">دَوْر الآن 🎯</button>
        <div id="result"></div>
        <script>
            const canvas = document.getElementById('wheelCanvas');
            const ctx = canvas.getContext('2d');
            const sectors = [
                {label: "5,000", color: "#3b82f6"}, {label: "10,000", color: "#1d4ed8"},
                {label: "25,000", color: "#4f46e5"}, {label: "50,000", color: "#2563eb"},
                {label: "100,000", color: "#312e81"}, {label: "حظ أوفر", color: "#dc2626"},
                {label: "لفة مجانية", color: "#9333ea"}, {label: "1,000,000", color: "#1e40af"}
            ];
            const arc = Math.PI / (sectors.length / 2);
            let angle = 0, isSpinning = false;
            function drawWheel() {
                const center = canvas.width / 2;
                sectors.forEach((sector, i) => {
                    const sa = i * arc, ea = (i + 1) * arc;
                    ctx.beginPath(); ctx.moveTo(center, center); ctx.arc(center, center, center, sa, ea);
                    ctx.fillStyle = sector.color; ctx.fill(); ctx.save();
                    ctx.translate(center, center); ctx.rotate(sa + arc / 2);
                    ctx.textAlign = "right"; ctx.fillStyle = "#fff"; ctx.font = "bold 14px Tahoma";
                    ctx.fillText(sector.label, center - 25, 10); ctx.restore();
                });
            }
            drawWheel();
            function spinWheel() {
                if (isSpinning) return;
                isSpinning = true; document.getElementById('spinBtn').disabled = true;
                angle += Math.floor(1000 + Math.random() * 2000);
                canvas.style.transform = `rotate(${angle}deg)`;
                setTimeout(() => {
                    isSpinning = false;
                    const prize = sectors[Math.floor(sectors.length - ((angle % 360) / (360 / sectors.length))) % sectors.length].label;
                    document.getElementById('result').innerText = `🎉 مبروك! ربحت: ${prize} ليرة`;
                }, 4000);
            }
        </script>
    </body>
    </html>
    """

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    ADMIN_IDS.add(message.chat.id)
    show_admin_menu(message.chat.id)

def show_admin_menu(chat_id, message_id=None):
    m_status = "🔴 مفعّل (متوقف)" if SETTINGS["maintenance"] else "🟢 معطّل (يعمل)"
    b_status = f"🟢 مفعّل ({SETTINGS['deposit_bonus_percentage']}%)" if SETTINGS["deposit_bonus_active"] else "🔴 معطّل"
    
    text = (
        f"⚙️ **لوحة تحكم الإدارة:**\n\n"
        f"🛠 **وضع الصيانة:** {m_status}\n"
        f"🎯 **بونص الإيداع:** {b_status}\n"
        f"💳 **طرق الشحن:** `{list(CUSTOM_DEPOSIT_METHODS.keys())}`\n"
        f"💸 **طرق السحب:** `{CUSTOM_WITHDRAW_METHODS}`\n\n"
        f"👇 **اختر الإجراء:**"
    )
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("➕ إضافة طريقة شحن جديدة", callback_data="admin_add_dep"),
        telebot.types.InlineKeyboardButton("➕ إضافة طريقة سحب جديدة", callback_data="admin_add_wdr"),
        telebot.types.InlineKeyboardButton("➕ إضافة رصيد يدوي لـ ID", callback_data="admin_add_bal"),
        telebot.types.InlineKeyboardButton("➖ خصم رصيد يدوي من ID", callback_data="admin_sub_bal"),
        telebot.types.InlineKeyboardButton("📢 إرسال إعلان للكل", callback_data="admin_broadcast"),
        telebot.types.InlineKeyboardButton("🔄 تبديل وضع الصيانة", callback_data="admin_toggle_m"),
        telebot.types.InlineKeyboardButton("🎯 تفعيل/إيقاف البونص", callback_data="admin_toggle_bonus")
    )
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callbacks(call):
    if call.data == "admin_add_dep":
        bot.answer_callback_query(call.id)
        ADMIN_STATES[call.message.chat.id] = {"action": "new_dep_name"}
        msg = bot.send_message(call.message.chat.id, "💳 أرسل **اسم طريقة الشحن الجديدة**:")
        bot.register_next_step_handler(msg, process_new_dep_name)
    elif call.data == "admin_add_wdr":
        bot.answer_callback_query(call.id)
        ADMIN_STATES[call.message.chat.id] = {"action": "new_wdr_name"}
        msg = bot.send_message(call.message.chat.id, "💸 أرسل **اسم طريقة السحب الجديدة**:")
        bot.register_next_step_handler(msg, process_new_wdr_name)
    elif call.data == "admin_add_bal":
        bot.answer_callback_query(call.id)
        ADMIN_STATES[call.message.chat.id] = {"action": "add_bal_id"}
        msg = bot.send_message(call.message.chat.id, "➕ أرسل **معرف المستخدم (Telegram ID)** لإضافة الرصيد:")
        bot.register_next_step_handler(msg, process_admin_bal_id)
    elif call.data == "admin_sub_bal":
        bot.answer_callback_query(call.id)
        ADMIN_STATES[call.message.chat.id] = {"action": "sub_bal_id"}
        msg = bot.send_message(call.message.chat.id, "➖ أرسل **معرف المستخدم (Telegram ID)** لخصم الرصيد:")
        bot.register_next_step_handler(msg, process_admin_bal_id)
    elif call.data == "admin_broadcast":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📢 أرسل الإعلان الآن:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, execute_broadcast)
    elif call.data == "admin_toggle_m":
        SETTINGS["maintenance"] = not SETTINGS["maintenance"]
        bot.answer_callback_query(call.id, "✅ تم التغيير!")
        show_admin_menu(call.message.chat.id, call.message.message_id)
    elif call.data == "admin_toggle_bonus":
        SETTINGS["deposit_bonus_active"] = not SETTINGS["deposit_bonus_active"]
        bot.answer_callback_query(call.id, "✅ تم التغيير!")
        show_admin_menu(call.message.chat.id, call.message.message_id)

def process_new_dep_name(message):
    admin_id = message.chat.id
    name = message.text.strip()
    ADMIN_STATES[admin_id]["dep_name"] = name
    ADMIN_STATES[admin_id]["action"] = "new_dep_details"
    msg = bot.send_message(admin_id, f"📍 أرسل **العنوان أو الرقم المخصص** لـ ({name}):")
    bot.register_next_step_handler(msg, process_new_dep_details)

def process_new_dep_details(message):
    admin_id = message.chat.id
    details = message.text.strip()
    dep_name = ADMIN_STATES[admin_id]["dep_name"]
    CUSTOM_DEPOSIT_METHODS[dep_name] = details
    bot.send_message(admin_id, f"✅ تمت إضافة طريقة الشحن ({dep_name}) بنجاح!")
    del ADMIN_STATES[admin_id]
    show_admin_menu(admin_id)

def process_new_wdr_name(message):
    admin_id = message.chat.id
    name = message.text.strip()
    CUSTOM_WITHDRAW_METHODS.append(name)
    bot.send_message(admin_id, f"✅ تمت إضافة طريقة السحب ({name}) بنجاح!")
    del ADMIN_STATES[admin_id]
    show_admin_menu(admin_id)

def process_admin_bal_id(message):
    admin_id = message.chat.id
    if admin_id not in ADMIN_STATES: return
    try:
        target_user = int(message.text.strip())
        ADMIN_STATES[admin_id]["target_user"] = target_user
        action_type = ADMIN_STATES[admin_id]["action"]
        if "add" in action_type:
            ADMIN_STATES[admin_id]["action"] = "add_bal_amount"
            msg = bot.send_message(admin_id, "💰 أرسل **المبلغ المراد إضافته**:")
        else:
            ADMIN_STATES[admin_id]["action"] = "sub_bal_amount"
            msg = bot.send_message(admin_id, "💸 أرسل **المبلغ المراد خصمه**:")
        bot.register_next_step_handler(msg, process_admin_bal_amount)
    except ValueError:
        msg = bot.send_message(admin_id, "❌ المعرف غير صحيح. أرسل رقم ID صحيح:")
        bot.register_next_step_handler(msg, process_admin_bal_id)

def process_admin_bal_amount(message):
    admin_id = message.chat.id
    if admin_id not in ADMIN_STATES: return
    try:
        amount = float(message.text.strip())
        state = ADMIN_STATES[admin_id]
        target_user = state["target_user"]
        action_type = state["action"]
        if "add" in action_type:
            USER_BALANCES[target_user] = USER_BALANCES.get(target_user, 0) + amount
            bot.send_message(admin_id, f"✅ تم إضافة {amount} للمستخدم `{target_user}`.", parse_mode="Markdown")
            try: bot.send_message(target_user, f"🎉 **تم شحن حسابك بواسطة الإدارة!**\n💰 المبلغ: `{amount}`", parse_mode="Markdown")
            except Exception: pass
        else:
            USER_BALANCES[target_user] = max(0, USER_BALANCES.get(target_user, 0) - amount)
            bot.send_message(admin_id, f"✅ تم خصم {amount} من المستخدم `{target_user}`.", parse_mode="Markdown")
            try: bot.send_message(target_user, f"⚠️ **تم خصم مبلغ من رصيدك بواسطة الإدارة.**\n💸 المبلغ: `{amount}`", parse_mode="Markdown")
            except Exception: pass
        del ADMIN_STATES[admin_id]
        show_admin_menu(admin_id)
    except ValueError:
        msg = bot.send_message(admin_id, "❌ القيمة غير صحيحة:")
        bot.register_next_step_handler(msg, process_admin_bal_amount)

def execute_broadcast(message):
    success, fail = 0, 0
    bot.send_message(message.chat.id, "⏳ جاري الإرسال...")
    for uid in USER_IDS:
        try:
            if message.photo: bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption or "", parse_mode="Markdown")
            else: bot.send_message(uid, message.text, parse_mode="Markdown")
            success += 1
        except Exception: fail += 1
    bot.send_message(message.chat.id, f"📊 تم بنجاح: {success} | فشل: {fail}")
    show_admin_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("dep_acc_") or call.data.startswith("dep_rej_"))
def handle_deposit_review(call):
    data_parts = call.data.split("_")
    action = data_parts[1]
    req_id = data_parts[2]
    if req_id not in PENDING_DEPOSITS:
        bot.answer_callback_query(call.id, "⚠️ الطلب غير موجود.")
        return
    dep_info = PENDING_DEPOSITS[req_id]
    user_id = dep_info["user_id"]
    amount = float(dep_info["amount"])
    final_amount = amount + (amount * (SETTINGS["deposit_bonus_percentage"] / 100)) if SETTINGS["deposit_bonus_active"] else amount
    
    if action == "acc":
        USER_BALANCES[user_id] = USER_BALANCES.get(user_id, 0) + final_amount
        bot.answer_callback_query(call.id, "✅ تمت الموافقة!")
        bot.edit_message_text(call.message.text + f"\n\n🟢 **الحالة:** تم القبول وإضافة {final_amount}", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        bot.send_message(user_id, f"🎉 **تم قبول الشحن وإضافة `{final_amount}` ليرة!**", parse_mode="Markdown")
        del PENDING_DEPOSITS[req_id]
    elif action == "rej":
        bot.answer_callback_query(call.id, "❌ أرسل سبب الرفض:")
        ADMIN_STATES[call.message.chat.id] = {"target_user": user_id, "req_id": req_id}
        msg = bot.send_message(call.message.chat.id, "✍️ أرسل سبب رفض الشحن:")
        bot.register_next_step_handler(msg, process_admin_rejection_reason)

def process_admin_rejection_reason(message):
    admin_id = message.chat.id
    if admin_id not in ADMIN_STATES: return
    reason = message.text.strip()
    state = ADMIN_STATES[admin_id]
    user_id = state["target_user"]
    req_id = state["req_id"]
    bot.send_message(user_id, f"❌ **عذراً، فشلت عملية الشحن!**\n\n⚠️ **السبب:** {reason}", parse_mode="Markdown")
    bot.send_message(admin_id, "✅ تم إرسال السبب للزبون.")
    if req_id in PENDING_DEPOSITS: del PENDING_DEPOSITS[req_id]
    del ADMIN_STATES[admin_id]

def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("👤 إنشاء حساب"),
        telebot.types.KeyboardButton("💳 شحن الرصيد"),
        telebot.types.KeyboardButton("💸 سحب الرصيد"),
        telebot.types.KeyboardButton("🎰 عجلة الفرصة"),
        telebot.types.KeyboardButton("📊 حسابي والمعلومات"),
        telebot.types.KeyboardButton("📜 شروط الاستخدام"),
        telebot.types.KeyboardButton("🎧 خدمة الدعم")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_terms(message):
    USER_IDS.add(message.chat.id)
    if check_maintenance(message): return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ موافقة على الشروط", callback_data="accept_terms"))
    bot.send_message(message.chat.id, "مرحباً بك. يرجى قراءة الشروط والأحكام قبل البدء:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "accept_terms")
def terms_accepted(call):
    USER_IDS.add(call.message.chat.id)
    bot.answer_callback_query(call.id, "تم القبول!")
    bot.send_message(call.message.chat.id, "أهلاً بك!", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == "🎧 خدمة الدعم")
def support_contact(message):
    USER_IDS.add(message.chat.id)
    if check_maintenance(message): return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("💬 تواصل مع الدعم الفني", url=SETTINGS["support_link"]))
    bot.send_message(message.chat.id, "🎧 للتواصل مع الدعم الفني:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "👤 إنشاء حساب")
def ask_username(message):
    USER_IDS.add(message.chat.id)
    if check_maintenance(message): return
    msg = bot.send_message(message.chat.id, "👤 أرسل **اسم المستخدم (Username)**

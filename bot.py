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
    "deposit_bonus_active": False,
    "deposit_bonus_percentage": 10,
    "support_link": "https://t.me/odairobertbot"
}

CUSTOM_DEPOSIT_METHODS = {
    "شام كاش": "يرجى التواصل مع الإدارة للحصول على التحويل",
    "سيرياتل كاش": "يرجى التواصل مع الإدارة للحصول على الرقم"
}

CUSTOM_WITHDRAW_METHODS = ["شام كاش", "سيرياتل كاش"]
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
        bot.send_message(message.chat.id, "⚠️ **البوت قيد الصيانة حالياً!**\nيرجى المحاولة لاحقاً.", parse_mode="Markdown")
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
    return """<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>عجلة الفرصة</title><style>body { background: #0f172a; color: #fff; font-family: Tahoma, sans-serif; text-align: center; padding: 20px; } h2 { color: #facc15; } .wheel-container { position: relative; width: 280px; height: 280px; margin: 20px auto; } canvas { width: 100%; height: 100%; border-radius: 50%; border: 5px solid #facc15; } button { background: #f59e0b; color: white; border: none; padding: 12px 30px; font-size: 18px; font-weight: bold; border-radius: 25px; cursor: pointer; margin-top: 15px; } #result { margin-top: 15px; font-size: 18px; color: #4ade80; font-weight: bold; }</style></head><body><h2>⭐ عجلة الفرصة ⭐</h2><div class="wheel-container"><canvas id="wheelCanvas" width="280" height="280"></canvas></div><button onclick="spinWheel()">دَوْر الآن 🎯</button><div id="result"></div><script>const canvas = document.getElementById('wheelCanvas'); const ctx = canvas.getContext('2d'); const sectors = ["5,000", "10,000", "25,000", "50,000", "100,000", "حظ أوفر", "لفة مجانية", "1,000,000"]; const colors = ["#3b82f6", "#1d4ed8", "#4f46e5", "#2563eb", "#312e81", "#dc2626", "#9333ea", "#1e40af"]; function drawWheel() { const arc = Math.PI / 4; sectors.forEach((s, i) => { ctx.beginPath(); ctx.moveTo(140, 140); ctx.arc(140, 140, 140, i*arc, (i+1)*arc); ctx.fillStyle = colors[i]; ctx.fill(); ctx.save(); ctx.translate(140, 140); ctx.rotate(i*arc + arc/2); ctx.textAlign = "right"; ctx.fillStyle = "#fff"; ctx.font = "bold 12px Tahoma"; ctx.fillText(s, 120, 5); ctx.restore(); }); } drawWheel(); function spinWheel() { const win = sectors[Math.floor(Math.random() * sectors.length)]; document.getElementById('result').innerText = '🎉 نتيجة العجلة: ' + win; }</script></body></html>"""

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    ADMIN_IDS.add(message.chat.id)
    show_admin_menu(message.chat.id)

def show_admin_menu(chat_id, message_id=None):
    m_status = "🔴 مفعّل" if SETTINGS["maintenance"] else "🟢 معطّل"
    b_status = f"🟢 مفعّل ({SETTINGS['deposit_bonus_percentage']}%)" if SETTINGS["deposit_bonus_active"] else "🔴 معطّل"
    
    text = (
        f"⚙️ **لوحة تحكم الإدارة:**\n\n"
        f"🛠 **وضع الصيانة:** {m_status}\n"
        f"🎯 **بونص الإيداع:** {b_status}\n"
        f"💳 **طرق الشحن:** `{list(CUSTOM_DEPOSIT_METHODS.keys())}`\n"
        f"💸 **طرق السحب:** `{CUSTOM_WITHDRAW_METHODS}`\n"
    )
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        telebot.types.InlineKeyboardButton("➕ إضافة طريقة شحن", callback_data="admin_add_dep"),
        telebot.types.InlineKeyboardButton("➕ إضافة طريقة سحب", callback_data="admin_add_wdr"),
        telebot.types.InlineKeyboardButton("➕ إضافة رصيد لزبون", callback_data="admin_add_bal"),
        telebot.types.InlineKeyboardButton("➖ خصم رصيد من زبون", callback_data="admin_sub_bal"),
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
        msg = bot.send_message(call.message.chat.id, "💳 أرسل اسم طريقة الشحن الجديدة:")
        bot.register_next_step_handler(msg, process_new_dep_name)
    elif call.data == "admin_add_wdr":
        bot.answer_callback_query(call.id)
        ADMIN_STATES[call.message.chat.id] = {"action": "new_wdr_name"}
        msg = bot.send_message(call.message.chat.id, "💸 أرسل اسم طريقة السحب الجديدة:")
        bot.register_next_step_handler(msg, process_new_wdr_name)
    elif call.data == "admin_add_bal":
        bot.answer_callback_query(call.id)
        ADMIN_STATES[call.message.chat.id] = {"action": "add_bal_id"}
        msg = bot.send_message(call.message.chat.id, "➕ أرسل معرف المستخدم (Telegram ID):")
        bot.register_next_step_handler(msg, process_admin_bal_id)
    elif call.data == "admin_sub_bal":
        bot.answer_callback_query(call.id)
        ADMIN_STATES[call.message.chat.id] = {"action": "sub_bal_id"}
        msg = bot.send_message(call.message.chat.id, "➖ أرسل معرف المستخدم (Telegram ID):")
        bot.register_next_step_handler(msg, process_admin_bal_id)
    elif call.data == "admin_broadcast":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📢 أرسل نص الإعلان:")
        bot.register_next_step_handler(msg, execute_broadcast)
    elif call.data == "admin_toggle_m":
        SETTINGS["maintenance"] = not SETTINGS["maintenance"]
        bot.answer_callback_query(call.id, "✅ تم!")
        show_admin_menu(call.message.chat.id, call.message.message_id)
    elif call.data == "admin_toggle_bonus":
        SETTINGS["deposit_bonus_active"] = not SETTINGS["deposit_bonus_active"]
        bot.answer_callback_query(call.id, "✅ تم!")
        show_admin_menu(call.message.chat.id, call.message.message_id)

def process_new_dep_name(message):
    admin_id = message.chat.id
    name = message.text.strip()
    ADMIN_STATES[admin_id]["dep_name"] = name
    msg = bot.send_message(admin_id, f"📍 أرسل تفاصيل أو عنوان ({name}):")
    bot.register_next_step_handler(msg, process_new_dep_details)

def process_new_dep_details(message):
    admin_id = message.chat.id
    details = message.text.strip()
    dep_name = ADMIN_STATES[admin_id]["dep_name"]
    CUSTOM_DEPOSIT_METHODS[dep_name] = details
    bot.send_message(admin_id, f"✅ تمت إضافة ({dep_name})!")
    if admin_id in ADMIN_STATES: del ADMIN_STATES[admin_id]
    show_admin_menu(admin_id)

def process_new_wdr_name(message):
    admin_id = message.chat.id
    name = message.text.strip()
    CUSTOM_WITHDRAW_METHODS.append(name)
    bot.send_message(admin_id, f"✅ تمت إضافة طريقة السحب ({name})!")
    if admin_id in ADMIN_STATES: del ADMIN_STATES[admin_id]
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
            msg = bot.send_message(admin_id, "💰 أرسل المبلغ المراد إضافته:")
        else:
            ADMIN_STATES[admin_id]["action"] = "sub_bal_amount"
            msg = bot.send_message(admin_id, "💸 أرسل المبلغ المراد خصمه:")
        bot.register_next_step_handler(msg, process_admin_bal_amount)
    except ValueError:
        msg = bot.send_message(admin_id, "❌ المعرف غير صحيح، أرسل رقم ID صحيح:")
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
            bot.send_message(admin_id, f"✅ تم إضافة {amount} لـ `{target_user}`.", parse_mode="Markdown")
            try: bot.send_message(target_user, f"🎉 تم شحن حسابك بمبلغ: `{amount}` ليرة", parse_mode="Markdown")
            except Exception: pass
        else:
            USER_BALANCES[target_user] = max(0, USER_BALANCES.get(target_user, 0) - amount)
            bot.send_message(admin_id, f"✅ تم خصم {amount} من `{target_user}`.", parse_mode="Markdown")
            try: bot.send_message(target_user, f"⚠️ تم خصم مبلغ `{amount}` ليرة من حسابك.", parse_mode="Markdown")
            except Exception: pass
        del ADMIN_STATES[admin_id]
        show_admin_menu(admin_id)
    except ValueError:
        msg = bot.send_message(admin_id, "❌ القيمة غير صحيحة، أرسل رقماً:")
        bot.register_next_step_handler(msg, process_admin_bal_amount)

def execute_broadcast(message):
    success = 0
    bot.send_message(message.chat.id, "⏳ جاري الإرسال...")
    for uid in USER_IDS:
        try:
            bot.send_message(uid, message.text)
            success += 1
        except Exception: pass
    bot.send_message(message.chat.id, f"📊 تم الإرسال لـ {success} مستخدم.")
    show_admin_menu(message.chat.id)

def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("👤 إنشاء حساب"),
        telebot.types.KeyboardButton("💳 شحن الرصيد"),
        telebot.types.KeyboardButton("💸 سحب الرصيد"),
        telebot.types.KeyboardButton("🎰 عجلة الفرصة"),
        telebot.types.KeyboardButton("📊 حسابي والمعلومات"),
        telebot.types.KeyboardButton("🎧 خدمة الدعم")
    )
    return markup

@bot.message_handler(commands=['start'])
def send
        

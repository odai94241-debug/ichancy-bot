import os
import time
import requests
import telebot
from flask import Flask, request

API_TOKEN = '8734379872:AAFpX_ZqN0_mdJhZW2gj1yiNYJDIAVUqp18'
AGENT_ID = "2826132-odai1@agents.nps"
ICHANCY_API_URL = "https://agents.ichancy.com/api/create_player"

SETTINGS = {
    "support_link": "https://t.me/odairobertbot"
}

CUSTOM_WITHDRAW_METHODS = ["شام كاش", "سيرياتل كاش"]
MIN_WITHDRAW = 500       

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

USER_BALANCES = {}
USER_IDS = set()
TEMP_USER_DATA = {}

@app.route(f'/{API_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return "Forbidden", 403

@app.route('/')
def index():
    return "iChancy Bot is Online and Healthy!", 200

def main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("👤 إنشاء حساب"),
        telebot.types.KeyboardButton("💳 شحن الرصيد"),
        telebot.types.KeyboardButton("💸 سحب الرصيد"),
        telebot.types.KeyboardButton("📊 حسابي والمعلومات"),
        telebot.types.KeyboardButton("🎧 خدمة الدعم")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_start(message):
    USER_IDS.add(message.chat.id)
    bot.send_message(message.chat.id, "أهلاً بك في البوت الرسمي!", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == "🎧 خدمة الدعم")
def support_contact(message):
    USER_IDS.add(message.chat.id)
    bot.send_message(message.chat.id, f"للتواصل مع الدعم الفني: {SETTINGS['support_link']}")

@bot.message_handler(func=lambda message: message.text == "👤 إنشاء حساب")
def ask_username(message):
    USER_IDS.add(message.chat.id)
    msg = bot.send_message(message.chat.id, "أرسل اسم المستخدم (Username):")
    bot.register_next_step_handler(msg, process_custom_username)

def process_custom_username(message):
    if message.text and message.text.startswith('/'): return
    username = message.text.strip()
    TEMP_USER_DATA[message.chat.id] = {"username": username}
    msg = bot.send_message(message.chat.id, "أرسل كلمة السر (Password):")
    bot.register_next_step_handler(msg, process_custom_password)

def process_custom_password(message):
    if message.text and message.text.startswith('/'): return
    password = message.text.strip()
    user_id = message.chat.id
    username = TEMP_USER_DATA.get(user_id, {}).get("username", "user")
    try:
        payload = {"agent_id": AGENT_ID, "username": username, "password": password, "telegram_id": user_id}
        requests.post(ICHANCY_API_URL, json=payload, timeout=5)
    except Exception: pass
    bot.send_message(user_id, f"تم إنشاء الحساب بنجاح!\nالمستخدم: {username}\nكلمة السر: {password}", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == "💳 شحن الرصيد")
def deposit_info(message):
    USER_IDS.add(message.chat.id)
    bot.send_message(message.chat.id, "يرجى التواصل مع الدعم لشحن الرصيد.")

@bot.message_handler(func=lambda message: message.text == "💸 سحب الرصيد")
def withdraw_info(message):
    USER_IDS.add(message.chat.id)
    bot.send_message(message.chat.id, f"الحد الأدنى للسحب: {MIN_WITHDRAW} ليرة.")

@bot.message_handler(func=lambda message: message.text == "📊 حسابي والمعلومات")
def show_account_info(message):
    USER_IDS.add(message.chat.id)
    bal = USER_BALANCES.get(message.from_user.id, 0)
    bot.send_message(message.chat.id, f"معلومات الحساب:\nID: {message.from_user.id}\nالرصيد: {bal} ليرة")

# ضبط الـ Webhook تلقائياً مع سيرفر Render
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')
if RENDER_URL:
    try:
        bot.remove_webhook()
        time.sleep(0.2)
        bot.set_webhook(url=f"{RENDER_URL}/{API_TOKEN}")
    except Exception as e:
        print(f"Webhook error: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    

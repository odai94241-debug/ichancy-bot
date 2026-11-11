import os
from flask import Flask, request
import telebot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

# ⚠️ ضع التوكن الجديد الخاص بك هنا (من BotFather)
BOT_TOKEN = "9076616228:AAH44GZlaKbGDqMMQdkX4chUTWpZYbhA5hc"

# ⚠️ الأيدي الخاص بك
ADMIN_ID = 9145587774 

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

def main_menu(is_admin=False):
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(KeyboardButton("👤 حسابي"), KeyboardButton("🎧 الدعم"))
    if is_admin:
        m.add(KeyboardButton("⚙️ لوحة التحكم"))
    return m

@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.chat.id
    is_admin = uid == ADMIN_ID
    bot.send_message(uid, f"✨ أهلاً بك!\n🆔 ايديك: {uid}", reply_markup=main_menu(is_admin))

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_all(message):
    uid = message.chat.id
    if uid == ADMIN_ID and message.text == "⚙️ لوحة التحكم":
        bot.send_message(uid, "أهلاً بك يا مدير.")
    else:
        bot.send_message(uid, "هذا الخيار قيد التطوير.")

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
    url = "https://ichancy-bot-2.onrender.com/webhook"
    result = bot.set_webhook(url=url)
    return f"Webhook set to {url} | result={result}", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

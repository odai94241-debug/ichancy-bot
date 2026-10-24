import os
from flask import Flask, request
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = '8734379872:AAFpX_ZqN0_mdJhZW2gj1yiNYJDIAVUqp18'
MIN_WITHDRAWAL = 500

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# لوحة الأزرار الرئيسية
def main_menu():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("👤 إنشاء حساب"),
        KeyboardButton("💳 شحن الرصيد"),
        KeyboardButton("💸 سحب الرصيد"),
        KeyboardButton("📊 حسابي والمعلومات"),
        KeyboardButton("🎧 خدمة الدعم")
    )
    return markup

# الصفحة الرئيسية لمعرفة أن السيرفر يعمل
@app.route('/', methods=['GET'])
def index():
    return 'iChancy Bot is Online!', 200

# استقبال الـ Webhook وتمريره للبوت
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

# أمر Start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "مرحباً بك في بوت إدارة وكالة **iChancy** الرسمية! 🎰\n\n"
        "يمكنك استخدام الأزرار أدناه للتحكم بحسابك وشحن أو سحب الأرباح بسهولة."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

# معالجة الضغط على الأزرار
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text

    if text == "👤 إنشاء حساب":
        bot.reply_to(message, "لإنشاء حساب جديد في الوكالة، يرجى إرسال اسم المستخدم المطلوب برمز (Username):")

    elif text == "💳 شحن الرصيد":
        bot.reply_to(message, "لطلب شحن الرصيد، يرجى التواصل مع الدعم أو كتابة المبلغ المراد شحنه مع معرف حسابك.")

    elif text == "💸 سحب الرصيد":
        msg = f"⚠️ **حد السحب الأدنى هو {MIN_WITHDRAWAL} نقطة/عملة.**\n\nيرجى كتابة رقم حسابك والمبلغ المراد سحبه:"
        bot.reply_to(message, msg, parse_mode="Markdown")

    elif text == "📊 حسابي والمعلومات":
        info = (
            f"👤 **معلومات الحساب:**\n"
            f"• الاسم: {message.from_user.first_name}\n"
            f"• المعرف (ID): `{message.chat.id}`\n"
            f"• حد السحب الأدنى: {MIN_WITHDRAWAL}"
        )
        bot.reply_to(message, info, parse_mode="Markdown")

    elif text == "🎧 خدمة الدعم":
        bot.reply_to(message, "للتواصل المباشر مع الدعم الفني للوكالة، يرجى إرسال استفسارك هنا وسيقوم الآدمن بالرد عليك.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    

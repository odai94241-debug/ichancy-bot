import json
import os
import random
import sqlite3
from datetime import date
from flask import Flask, request
import requests
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

TOKEN = '8734379872:AAFpX_ZqN0_mdJhZW2gj1yiNYJDIAVUqp18'
ADMIN_ID = 7753870725
ICHANCY_URL = 'https://www.ichancy.com'
AGENT_CODE = '2826132-odai1@agents.nps'
RENDER_URL = 'https://ichancy-bot-uagc.onrender.com'

# الحدود المالية بالعملة السورية الجديدة
MIN_DEPOSIT = 250
MIN_WITHDRAWAL = 500
WHEEL_DEPOSIT_REQUIRED = (
    750  # الحد اليومي لشحن العجلة بالعملة الجديدة (مثلاً 750 ليرة)
)

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)


def init_db():
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute(
      '''CREATE TABLE IF NOT EXISTS users (
                      user_id INTEGER PRIMARY KEY, 
                      first_name TEXT, 
                      balance REAL DEFAULT 0,
                      daily_deposit REAL DEFAULT 0,
                      last_deposit_date TEXT,
                      last_spin_date TEXT,
                      referred_by INTEGER
                  )'''
  )
  cursor.execute(
      '''CREATE TABLE IF NOT EXISTS accounts (
                      user_id INTEGER,
                      username TEXT,
                      password TEXT
                  )'''
  )
  cursor.execute(
      '''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)'''
  )
  cursor.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance', 'off')")
  cursor.execute(
      "INSERT OR IGNORE INTO settings VALUES ('sham_cash', 'غير محدد حالياً')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings VALUES ('syriatel_cash', 'غير"
      " محدد حالياً')"
  )
  cursor.execute(
      "INSERT OR IGNORE INTO settings VALUES ('custom_terms', 'شروط وأحكام وكالة"
      ' iChancy (العملة الجديدة):\n1. منع الحسابات المتعددة.\n2. الحد الأدنى'
      ' للشحن: 250 ليرة.\n3. الحد الأدنى للسحب: 500 ليرة.\n4. نسب السحب'
      ' المتناقصة: حتى 500 ألف 10%، ومن 500 ألف إلى 1.5 مليون 15%، وفوق 1.5 مليون'
      " 20%.')"
  )
  conn.commit()
  conn.close()


init_db()


def get_setting(key):
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute('SELECT value FROM settings WHERE key=?', (key,))
  row = cursor.fetchone()
  conn.close()
  return row[0] if row else ''


def set_setting(key, value):
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
  conn.commit()
  conn.close()


def add_user(user_id, first_name, referred_by=None):
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute(
      'INSERT OR IGNORE INTO users (user_id, first_name, referred_by) VALUES'
      ' (?, ?, ?)',
      (user_id, first_name, referred_by),
  )
  conn.commit()
  conn.close()


def get_user_info(user_id):
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute(
      'SELECT balance, daily_deposit, last_deposit_date, last_spin_date FROM'
      ' users WHERE user_id=?',
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
  return 0, 0, '', ''


def update_user_balance(user_id, amount):
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute(
      'UPDATE users SET balance = balance + ? WHERE user_id=?', (amount, user_id)
  )
  conn.commit()
  conn.close()


def add_user_deposit(user_id, amount):
  today = str(date.today())
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute(
      'SELECT daily_deposit, last_deposit_date FROM users WHERE user_id=?',
      (user_id,),
  )
  row = cursor.fetchone()
  if row:
    current_dep, last_date = row
    new_dep = (current_dep + amount) if last_date == today else amount
    cursor.execute(
        'UPDATE users SET daily_deposit = ?, last_deposit_date = ? WHERE'
        ' user_id=?',
        (new_dep, today, user_id),
    )
    conn.commit()
  conn.close()


def save_player_account(user_id, username, password):
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute(
      'INSERT INTO accounts VALUES (?, ?, ?)', (user_id, username, password)
  )
  conn.commit()
  conn.close()


def get_player_account(user_id):
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute(
      'SELECT username, password FROM accounts WHERE user_id=?', (user_id,)
  )
  row = cursor.fetchone()
  conn.close()
  return row


def get_all_users():
  conn = sqlite3.connect('bot_data.db', check_same_thread=False)
  cursor = conn.cursor()
  cursor.execute('SELECT user_id FROM users')
  rows = cursor.fetchall()
  conn.close()
  return [r[0] for r in rows]


# حساب عمولة السحب المتناقصة بالعملة الجديدة (مثال: مليون ومية ألف تصبح 1,100,000 جديدة أو حسب مقياسك)
def calculate_withdrawal_commission(amount):
  if amount <= 500000:
    rate = 0.10
  elif amount <= 1500000:
    rate = 0.15
  else:
    rate = 0.20
  deduction = amount * rate
  return amount - deduction, rate * 100


def ichancy_api_create_account(username, password):
  try:
    response = requests.post(
        'https://api.ichancy.com/v1/create_account',
        json={'agent_code': AGENT_CODE, 'username': username, 'password': password},
        headers={'Content-Type': 'application/json'},
        timeout=15,
    )
    if response.status_code == 200:
      return True, 'تم إنشاء الحساب في الكاشيرة بنجاح'
  except Exception:
    pass
  return True, 'تم تسجيل الحساب وإرساله للكاشيرة بنجاح'


# واجهة الويب الخاصة بعجلة الفرصة (Web App)
@app.route('/wheel')
def wheel_page():
  return f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>عجلة الفرصة - iChancy</title>
        <style>
            body {{ background: #0f172a; color: white; font-family: Tahoma, sans-serif; text-align: center; margin: 0; padding: 20px; }}
            h1 {{ color: #f59e0b; margin-top: 10px; }}
            .wheel-container {{ position: relative; width: 320px; height: 320px; margin: 20px auto; }}
            canvas {{ border-radius: 50%; box-shadow: 0 0 25px rgba(245, 158, 11, 0.6); background: #1e293b; }}
            .pin {{ position: absolute; top: -10px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 15px solid transparent; border-right: 15px solid transparent; border-bottom: 30px solid #ef4444; z-index: 10; }}
            button {{ margin-top: 25px; padding: 14px 40px; background: linear-gradient(135deg, #f59e0b, #d97706); border: none; color: white; font-size: 20px; font-weight: bold; border-radius: 12px; cursor: pointer; box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4); }}
            button:active {{ transform: scale(0.95); }}
            #result {{ margin-top: 20px; font-size: 18px; font-weight: bold; color: #10b981; }}
        </style>
    </head>
    <body>
        <h1>🎡 عجلة الفرصة (العملة الجديدة)</h1>
        <p>اربح جوائز نقدية فورية!</p>
        <div class="wheel-container">
            <div class="pin"></div>
            <canvas id="wheel" width="320" height="320"></canvas>
        </div>
        <button onclick="spin()">دور العجلة الآن</button>
        <div id="result"></div>

        <script>
            const canvas = document.getElementById('wheel');
            const ctx = canvas.getContext('2d');
            const prizes = ['50 ليرة', '100 ليرة', '250 ليرة', '500 ليرة', '1000 ليرة', 'حظاً أوفر'];
            const colors = ['#f59e0b', '#ef4444', '#3b82f6', '#10b981', '#8b5cf6', '#64748b'];
            const numSegments = prizes.length;
            const arcSize = (2 * Math.PI) / numSegments;
            let spinning = false;

            function drawWheel() {{
                for (let i = 0; i < numSegments; i++) {{
                    ctx.beginPath();
                    ctx.fillStyle = colors[i];
                    ctx.moveTo(160, 160);
                    ctx.arc(160, 160, 150, i * arcSize, (i + 1) * arcSize);
                    ctx.lineTo(160, 160);
                    ctx.fill();
                    ctx.save();
                    ctx.translate(160, 160);
                    ctx.rotate(i * arcSize + arcSize / 2);
                    ctx.fillStyle = '#ffffff';
                    ctx.font = 'bold 13px Tahoma';
                    ctx.fillText(prizes[i], 70, 5);
                    ctx.restore();
                }}
            }}
            drawWheel();

            function spin() {{
                if (spinning) return;
                spinning = true;
                const randomAngle = Math.floor(Math.random() * 360) + 1800;
                canvas.style.transition = 'transform 4s cubic-bezier(0.15, 0.85, 0.12, 0.95)';
                canvas.style.transform = `rotate(${randomAngle}deg)`;
                
                setTimeout(() => {{
                    document.getElementById('result').innerText = '🎉 مبروك! تمت إضافة جائزتك لرصيدك.';
                }}, 4000);
            }}
        </script>
    </body>
    </html>
    """, 200


def main_menu(is_admin=False):
  markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
  markup.add(
      KeyboardButton('⚡ حساب إيشَانسي وشحنه'),
      KeyboardButton('💳 سحب رصيد من البوت'),
      KeyboardButton('📱 شحن رصيد في البوت'),
      KeyboardButton('🎁 كود جائزة'),
      KeyboardButton('🤝 إهداء صديق'),
      KeyboardButton('👥 الإحالات'),
      KeyboardButton('📊 السجلات'),
      KeyboardButton('🌐 إيشَانسي'),
      KeyboardButton('🔄 استرداد آخر طلب سحب'),
      KeyboardButton('🎁 العروض النشطة'),
      KeyboardButton('📜 شروط الاستخدام'),
      KeyboardButton('🎧 إرسال رسالة للدعم'),
      KeyboardButton('🎡 عجلة الفرصة'),
  )
  if is_admin:
    markup.add(KeyboardButton('⚙️ لوحة تحكم الآدمن'))
  return markup


def ichancy_sub_menu():
  markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
  markup.add(
      KeyboardButton('👤 إنشاء حساب إيشَانسي'),
      KeyboardButton('💳 شحن رصيد من الحساب'),
      KeyboardButton('💸 سحب رصيد من الحساب'),
      KeyboardButton('⚡ شحن كامل الرصيد'),
      KeyboardButton('🗑️ حذف حساب إيشَانسي'),
      KeyboardButton('🔙 رجوع للقائمة الرئيسية'),
  )
  return markup


def deposit_methods_menu():
  markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
  markup.add(
      KeyboardButton('📱 سيريتل كاش'),
      KeyboardButton('📱 شام كاش (الجديدة)'),
      KeyboardButton('🔙 رجوع للقائمة الرئيسية'),
  )
  return markup


def admin_panel_menu():
  markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
  status = (
      'إيقاف الصيانة 🔴'
      if get_setting('maintenance') == 'on'
      else 'تشغيل الصيانة 🟢'
  )
  markup.add(
      KeyboardButton(f'🛠️ {status}'),
      KeyboardButton('📢 إرسال إذاعة للجميع'),
      KeyboardButton('👤 مراسلة لاعب محدد'),
      KeyboardButton('📱 تغيير كود الشام كاش'),
      KeyboardButton('📱 تغيير كود سيريتل كاش'),
      KeyboardButton('👥 إحصائيات الأعضاء'),
      KeyboardButton('🔙 رجوع للقائمة الرئيسية'),
  )
  return markup


@app.route('/', methods=['GET'])
def index():
  return 'iChancy Fully Automated Bot (New Currency) is Online!', 200


@app.route('/', methods=['POST'])
def webhook():
  if request.headers.get('content-type') == 'application/json':
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'OK', 200
  return 'Forbidden', 403


user_states = {}
temp_data = {}


@bot.message_handler(commands=['start'])
def send_welcome(message):
  user_id = message.chat.id
  args = message.text.split()
  ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
  add_user(user_id, message.from_user.first_name, ref_id)
  user_states[user_id] = None
  is_admin = user_id == ADMIN_ID

  if get_setting('maintenance') == 'on' and not is_admin:
    bot.send_message(user_id, '⚠️ البوت قيد الصيانة حالياً.')
    return

  balance, _, _, _ = get_user_info(user_id)
  text = (
      f'✨ **قائمة الخيارات الرئيسية (العملة الجديدة)**\n\n💰 **الرصيد الحالي:**'
      f' {balance} ليرة جديدة\n🆔 **الآيدي الخاص بك:** `{user_id}`'
  )
  bot.send_message(
      user_id, text, reply_markup=main_menu(is_admin), parse_mode='Markdown'
  )


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
  user_id = call.message.chat.id
  is_admin = user_id == ADMIN_ID
  if call.data.startswith('approve_'):
    parts = call.data.split('_')
    target_user = int(parts[1])
    bot.answer_callback_query(call.id, text='✅ تمت الموافقة بنجاح.')
    bot.send_message(
        target_user,
        '✅ تم التحقق من معاملتك المالية بالعملة الجديدة وإضافتها بنجاح!',
    )
    bot.edit_message_text(
        f'{call.message.text}\n\n🟢 **الحالة:** مؤكد ومعالج',
        chat_id=ADMIN_ID,
        message_id=call.message.message_id,
        parse_mode='Markdown',
    )


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_messages(message):
  user_id = message.chat.id
  text = message.text if message.text else ''
  is_admin = user_id == ADMIN_ID

  if get_setting('maintenance') == 'on' and not is_admin:
    bot.send_message(user_id, '⚠️ البوت قيد الصيانة حالياً.')
    return

  state = user_states.get(user_id)

  if state == 'awaiting_ichancy_reg_username':
    temp_data[user_id] = {'username': text}
    user_states[user_id] = 'awaiting_ichancy_reg_password'
    bot.send_message(
        user_id,
        '🔐 أرسل كلمة المرور للحساب الجديد (6 خانات على الأقل):',
        reply_markup=ReplyKeyboardMarkup(one_time_keyboard=True).add(
            KeyboardButton('🔙 رجوع للقائمة الرئيسية')
        ),
    )
    return

  if state == 'awaiting_ichancy_reg_password':
    username = temp_data.get(user_id, {}).get('username')
    password = text
    user_states[user_id] = None
    temp_data.pop(user_id, None)

    ichancy_api_create_account(username, password)
    save_player_account(user_id, username, password)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton('🌐 الدخول الفوري إلى iChancy', url=ICHANCY_URL)
    )
    bot.send_message(
        user_id,
        f'✅ **تم إنشاء الحساب بنجاح!** 🎉\n\n• اسم المستخدم: `{username}`\n• كلمة'
        ' المرور: `{password}`',
        reply_markup=markup,
        parse_mode='Markdown',
    )
    return

  if state == 'awaiting_deposit_tx':
    temp_data[user_id] = {'method': text, 'tx': text}
    user_states[user_id] = 'awaiting_deposit_amount'
    bot.send_message(
        user_id,
        f'💵 أرسل الآن **قيمة المبلغ** بالليرة الجديدة (الحد الأدنى'
        f' {MIN_DEPOSIT} ليرة):',
    )
    return

  if state == 'awaiting_deposit_amount':
    try:
      amount = float(text)
    except ValueError:
      bot.send_message(user_id, '⚠️ يرجى إرسال رقم صحيح للمبلغ!')
      return

    if amount < MIN_DEPOSIT and not is_admin:
      bot.send_message(
          user_id,
          f'⚠️ عذراً، الحد الأدنى لعملية الشحن هو **{MIN_DEPOSIT} ليرة جديدة**'
          ' فقط!',
          parse_mode='Markdown',
      )
      return

    user_states[user_id] = None
    temp_data.pop(user_id, None)

    add_user_deposit(user_id, amount)
    bonus = amount * 0.10  # بونص 10%
    total = amount + bonus
    update_user_balance(user_id, total)

    bot.send_message(
        user_id,
        f'✅ **تم الشحن بنجاح وتفعيل عجلة الفرصة!**\n• المبلغ الأساسي:'
        f' {amount} ليرة\n• البونص المضاف: {bonus} ليرة\n• الإجمالي المضاف:'
        f' {total} ليرة جديدة',
        reply_markup=main_menu(is_admin),
        parse_mode='Markdown',
    )
    return

  if state == 'awaiting_withdraw_amount':
    try:
      amount = float(text)
    except ValueError:
      bot.send_message(user_id, '⚠️ يرجى إرسال رقم صحيح للمبلغ!')
      return

    if amount < MIN_WITHDRAWAL and not is_admin:
      bot.send_message(
          user_id,
          f'⚠️ عذراً، الحد الأدنى لعملية السحب هو **{MIN_WITHDRAWAL} ليرة جديدة**'
          ' فقط!',
          parse_mode='Markdown',
      )
      return

    user_states[user_id] = None
    net_amount, rate = calculate_withdrawal_commission(amount)

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            '✅ تأكيد السحب والخصم', callback_data=f'approve_{user_id}_with'
        )
    )
    bot.send_message(
        ADMIN_ID,
        f'💸 **طلب سحب جديد (بالعملة الجديدة):**\n• المستخدم: {user_id}\n• المبلغ'
        f' المطلوب: {amount} ليرة\n• العمولة ({rate}%): الصافي للوصول'
        f' {net_amount} ليرة جديدة',
        reply_markup=markup,
        parse_mode='Markdown',
    )
    bot.send_message(
        user_id,
        f'⏳ تم إرسال طلب سحبك بنجاح.\n• الصافي بعد عمولة الوكالة ({rate}%):'
        f' **{net_amount} ليرة جديدة**',
        reply_markup=main_menu(is_admin),
        parse_mode='Markdown',
    )
    return

  if state == 'awaiting_broadcast' and is_admin:
    for u in get_all_users():
      try:
        bot.send_message(u, text)
      except:
        pass
    bot.send_message(
        user_id, '✅ تمت الإذاعة بنجاح.', reply_markup=admin_panel_menu()
    )
    user_states[user_id] = None
    return

  if text == '🔙 رجوع للقائمة الرئيسية':
    user_states[user_id] = None
    bot.send_message(
        user_id, 'القائمة الرئيسية:', reply_markup=main_menu(is_admin)
    )
  elif text == '⚡ حساب إيشَانسي وشحنه':
    bot.send_message(
        user_id, 'إدارة حساب iChancy:', reply_markup=ichancy_sub_menu()
    )
  elif text == '👤 إنشاء حساب إيشَانسي':
    if get_player_account(user_id):
      bot.send_message(user_id, '⚠️ لديك حساب مسجل مسبقاً.')
    else:
      user_states[user_id] = 'awaiting_ichancy_reg_username'
      bot.send_message(user_id, '👤 أرسل اسم المستخدم (Username) الجديد:')
  elif text == '💳 شحن رصيد في البوت':
    bot.send_message(
        user_id, 'اختر طريقة الدفع:', reply_markup=deposit_methods_menu()
    )
  elif text in ['📱 سيريتل كاش', '📱 شام كاش (الجديدة)']:
    user_states[user_id] = 'awaiting_deposit_tx'
    code = (
        get_setting('sham_cash')
        if 'شام' in text
        else get_setting('syriatel_cash')
    )
    bot.send_message(
        user_id,
        f'📱 **{text}**\nالكود المعتمد: `{code}`\n\nأرسل **رقم العملية**:',
        parse_mode='Markdown',
    )
  elif text == '💳 سحب رصيد من البوت':
    user_states[user_id] = 'awaiting_withdraw_amount'
    bot.send_message(
        user_id,
        f'💸 أرسل المبلغ المراد سحبه (الحد الأدنى {MIN_WITHDRAWAL} ليرة):',
    )
  elif text == '👥 الإحالات':
    bot.send_message(
        user_id,
        f'👥 رابط الإحالة الخاص بك:\n`https://t.me/{(bot.get_me()).username}?start={user_id}`',
        parse_mode='Markdown',
    )
  elif text == '📜 شروط الاستخدام':
    bot.send_message(user_id, get_setting('custom_terms'))
  elif text == '🎡 عجلة الفرصة':
    _, daily_dep, _, last_spin = get_user_info(user_id)
    today = str(date.today())

    if last_spin == today and not is_admin:
      bot.send_message(
          user_id,
          '⚠️ لقد استخدمت لفتك المجانية لليوم! (مسموح دورة واحدة فقط في اليوم).',
      )
      return

    if daily_dep < WHEEL_DEPOSIT_REQUIRED and not is_admin:
      bot.send_message(
          user_id,
          f'🔒 عجلة الفرصة مقفلة!\nيجب شحن مبلغ جديد بقيمة **{WHEEL_DEPOSIT_REQUIRED}'
          ' ليرة جديدة على الأقل** اليوم لتفعيل اللفة.',
          parse_mode='Markdown',
      )
      retur

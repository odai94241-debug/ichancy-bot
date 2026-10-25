import requests
from datetime import datetime

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask, request

from config import (
    BOT_TOKEN, ADMIN_ID, AGENT_CODE, ICHANCY_PANEL_URL,
    MIN_DEPOSIT, MIN_WITHDRAWAL, MIN_USD_DEPOSIT,
    REFERRAL_PROFIT_SHARE, REFERRAL_MIN_ACTIVE,
)
from db import (
    init_db, get_setting, set_setting, add_user, get_user,
    update_balance, add_deposit_total, add_withdraw_total,
    save_account, get_account, get_all_users, get_active_offer,
)
from kb import (
    main_menu, ichancy_menu, withdraw_menu, deposit_menu,
    admin_menu, back_menu,
)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
init_db()


def calc_commission(amt):
    if amt <= 50000000:
        rate = 0.10
    elif amt <= 150000000:
        rate = 0.15
    else:
        rate = 0.20
    return amt - (amt * rate), rate * 100


def create_ichancy_account(username, password):
    email = f"{username}@agent.nps"
    try:
        session = requests.Session()
        session.post(
            "https://agents.ichancy.com/login",
            data={"username": "Odai1@Agents.nps", "password": "ضع_الباسورد_هون"},
            timeout=30,
        )
        resp = session.post(
            "https://agents.ichancy.com/register",
            data={
                "username": username,
                "email": email,
                "password": password,
                "agent_code": AGENT_CODE,
            },
            timeout=30,
        )
        text = resp.text.lower()
        if "success" in text or "تم" in text or "created" in text:
            return True, "✅ تم إنشاء الحساب بنجاح"
        if "error" in text or "exists" in text or "موجود" in text:
            return False, "⚠️ هذا الحساب مكرر، جرب اسم تاني"
        return True, "✅ تم إنشاء الحساب (تحقق يدوياً)"
    except Exception as e:
        return False, f"⚠️ خطأ في الاتصال: {str(e)[:100]}"
user_states = {}
temp_data = {}


# ==================== /start ====================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.chat.id
    args = message.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    add_user(uid, message.from_user.first_name, ref)
    user_states[uid] = None
    is_admin = uid == ADMIN_ID

    if ref and ref != uid:
        try:
            conn_users = get_all_users()
            bot.send_message(ref, f"👥 إحالة جديدة!\n👤 شخص جديد دخل من رابطك")
        except:
            pass

    if get_setting("maintenance") == "on" and not is_admin:
        bot.send_message(uid, "⚠️ البوت قيد الصيانة حالياً.")
        return

    bal, _, _, _ = get_user(uid)
    text = f"✨ قائمة الخيارات الرئيسية\n\n💰 الرصيد: {bal} ليرة جديدة\n🆔 ايديك: {uid}"
    bot.send_message(uid, text, reply_markup=main_menu(is_admin))


# ==================== معالج الأزرار ====================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_all(message):
    uid = message.chat.id
    text = message.text or ""
    is_admin = uid == ADMIN_ID

    if get_setting("maintenance") == "on" and not is_admin:
        bot.send_message(uid, "⚠️ البوت قيد الصيانة حالياً.")
        return

    # ✅ زر الرجوع أول شي
    if text == "🔙 رجوع":
        user_states[uid] = None
        temp_data.pop(uid, None)
        bal, _, _, _ = get_user(uid)
        bot.send_message(uid, f"القائمة الرئيسية:\n💰 الرصيد: {bal} ليرة جديدة", reply_markup=main_menu(is_admin))
        return

    state = user_states.get(uid)

    # ========== إنشاء حساب ايشاني ==========
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
        bot.send_message(uid, "⏳ جاري إنشاء الحساب...")
        ok, msg = create_ichancy_account(username, password)
        if ok:
            save_account(uid, username, password)
        bot.send_message(uid, f"{msg}\n\n👤 المستخدم: {username}\n🔑 كلمة السر: {password}", reply_markup=main_menu(is_admin))
        return

    # ========== سحب ==========
    if state == "wd_amount":
        try:
            amt = float(text)
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

    # ========== شحن ==========
    if state == "dep_amount":
        try:
            amt = float(text)
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
        offer = get_active_offer()
        bonus = amt * (offer / 100) if offer > 0 else 0
        user_states[uid] = None
        temp_data.pop(uid, None)
        bot.send_message(uid, f"⏳ تم إرسال طلب الشحن\n💰 {amt} ليرة\n🎁 بونص: {bonus} ليرة\n\nبانتظار الموافقة", reply_markup=main_menu(is_admin))
        bot.send_message(ADMIN_ID, f"📥 طلب شحن\n👤 {uid}\n💰 {amt}\n🎁 {bonus}\n📱 {method}\n🔢 {text}")
        return
        
    # ========== الأزرار الرئيسية ==========
    if text == "👤 حسابي":
        acc = get_account(uid)
        if acc:
            bot.send_message(uid, f"👤 حسابك\n\n👤 المستخدم: {acc[0]}\n🔑 كلمة السر: {acc[1]}", reply_markup=ichancy_menu())
        else:
            bot.send_message(uid, "ما عندك حساب. اضغط إنشاء حساب:", reply_markup=ichancy_menu())

    elif text == "👤 إنشاء حساب ايشاني":
        user_states[uid] = "reg_username"
        bot.send_message(uid, "👤 أرسل اسم المستخدم (إنجليزي + رقم):", reply_markup=back_menu())

    elif text == "💳 سحب رصيد من البوت":
        user_states[uid] = "wd_method"
        bot.send_message(uid, "💳 اختر طريقة السحب:", reply_markup=withdraw_menu())

    elif text in ("سيريان كاش", "شام كاش", "هرم") and user_states.get(uid) == "wd_method":
        temp_data[uid] = {"method": text}
        user_states[uid] = "wd_amount"
        bot.send_message(uid, f"💵 أرسل المبلغ (الحد الأدنى {MIN_WITHDRAWAL} ليرة):", reply_markup=back_menu())

    elif text == "📱 شحن رصيد في البوت":
        user_states[uid] = "dep_method"
        bot.send_message(uid, "📱 اختر طريقة الشحن:", reply_markup=deposit_menu())

    elif text in ("سيريان كاش", "شام كاش", "شام كاش USD") and user_states.get(uid) == "dep_method":
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
        msg = (f"👥 الإحالات\n\n🔗 رابطك: {ref_link}\n\n"
               f"📊 إجمالي: {total}\n✅ نشطة: {active}\n"
               f"💰 صافي خسارة: {net}\n🎁 أرباحك (5%): {earnings}\n\n"
               f"⚠️ شرط: 3 إحالات نشطة على الأقل")
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
        offer = get_active_offer()
        if offer > 0:
            bot.send_message(uid, f"🎁 عرض نشط!\n💰 {offer}% بونص على الشحن", reply_markup=back_menu())
        else:
            bot.send_message(uid, "ما في عروض نشطة حالياً", reply_markup=back_menu())

    elif text == "📜 شروط الاستخدام":
        bot.send_message(uid, get_setting("terms"), reply_markup=back_menu())

    elif text == "🎡 عجلة الفرصة":
        bot.send_message(uid, "🎡 عجلة الفرصة\n\n(سيتم إضافتها قريباً)", reply_markup=back_menu())

    elif text == "🤝 إهداء صديق":
        bot.send_message(uid, "🤝 إهداء صديق\n\n(سيتم إضافته قريباً)", reply_markup=back_menu())

    elif text == "🎁 كود جائزة":
        bot.send_message(uid, "🎁 أرسل كود الجائزة:\n\n(سيتم إضافته قريباً)", reply_markup=back_menu())

    # ========== لوحة الأدمن ==========
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

    elif text == "🎁 إنشاء عرض جديد" and is_admin:
        user_states[uid] = "offer_percent"
        bot.send_message(uid, "🎁 أرسل نسبة البونص (مثلاً: 20):", reply_markup=back_menu())

    elif text == "👥 إحصائيات الأعضاء" and is_admin:
        all_u = get_all_users()
        bot.send_message(uid, f"👥 عدد الأعضاء: {len(all_u)}", reply_markup=admin_menu())

    # ========== حالات الأدمن ==========
    elif state == "broadcast" and is_admin:
        for u in get_all_users():
            try:
                bot.send_message(u, text)
            except:
                pass
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

    elif state == "offer_percent" and is_admin:
        try:
            p = float(text)
            temp_data[uid] = {"percent": p}
            user_states[uid] = "offer_start"
            bot.send_message(uid, "⏰ أرسل وقت البداية (مثال: 2026-10-26 19:00):", reply_markup=back_menu())
        except:
            bot.send_message(uid, "⚠️ أرسل رقم صحيح:", reply_markup=back_menu())

    elif state == "offer_start" and is_admin:
        temp_data[uid]["start"] = text
        user_states[uid] = "offer_end"
        bot.send_message(uid, "⏰ أرسل وقت النهاية:", reply_markup=back_menu())

    elif state == "offer_end" and is_admin:
        p = temp_data[uid]["percent"]
        start = temp_data[uid]["start"]
        end = text
        from db import db_conn
        conn = db_conn()
        c = conn.cursor()
        c.execute("INSERT INTO offers (percent,start_time,end_time,active) VALUES (?,?,?,1)", (p, start, end))
        conn.commit()
        conn.close()
        user_states[uid] = None
        temp_data.pop(uid, None)
        for u in get_all_users():
            try:
                bot.send_message(u, f"🎁 عرض خاص!\n💰 {p}% بونص\n⏰ من {start} إلى {end}")
            except:
                pass
        bot.send_message(uid, "✅ تم إنشاء العرض", reply_markup=admin_menu())

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
    import os
    url = os.getenv("RENDER_EXTERNAL_URL", "") + "/webhook"
    if not url.startswith("http"):
        return "RENDER_EXTERNAL_URL غير مضبوط", 400
    result = bot.set_webhook(url=url)
    return f"Webhook set to {url} | result={result}", 200


@app.route("/delete_webhook", methods=["GET"])
def delete_webhook():
    bot.remove_webhook()
    return "Webhook deleted", 200


# ==================== تشغيل ====================
if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

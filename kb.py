from telebot.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu(is_admin=False):
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("👤 حسابي"),
        KeyboardButton("💳 سحب رصيد من البوت"),
        KeyboardButton("📱 شحن رصيد في البوت"),
        KeyboardButton("🤝 إهداء صديق"),
        KeyboardButton("🎁 كود جائزة"),
        KeyboardButton("👥 الإحالات"),
        KeyboardButton("📊 السجلات"),
        KeyboardButton("🎧 إرسال رسالة للدعم"),
        KeyboardButton("🌐 ايشاني"),
        KeyboardButton("🔄 استرداد آخر طلب سحب"),
        KeyboardButton("🎁 العروض النشطة"),
        KeyboardButton("📜 شروط الاستخدام"),
        KeyboardButton("🎡 عجلة الفرصة"),
    )
    if is_admin:
        m.add(KeyboardButton("⚙️ لوحة تحكم الآدمن"))
    return m


def ichancy_menu():
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("👤 إنشاء حساب ايشاني"),
        KeyboardButton("💳 سحب رصيد من الحساب"),
        KeyboardButton("💳 شحن رصيد في الحساب"),
        KeyboardButton("⚡ شحن كامل الرصيد"),
        KeyboardButton("🗑️ حذف حسابي"),
        KeyboardButton("🔙 رجوع"),
    )
    return m


def withdraw_menu():
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("سيرياتيل كاش"),
        KeyboardButton("شام كاش"),
        KeyboardButton("هرم"),
        KeyboardButton("🔙 رجوع"),
    )
    return m


def deposit_menu():
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("سيرياتيل كاش"),
        KeyboardButton("شام كاش"),
        KeyboardButton("شام كاش USD"),
        KeyboardButton("🔙 رجوع"),
    )
    return m


def admin_menu():
    m = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    m.add(
        KeyboardButton("🛠️ إيقاف/تشغيل الصيانة"),
        KeyboardButton("📢 إرسال إذاعة للجميع"),
        KeyboardButton("📱 تغيير كود الشام كاش"),
        KeyboardButton("📱 تغيير كود سيرياتيل كاش"),
        KeyboardButton("💵 تغيير سعر شام كاش دولار"),
        KeyboardButton("🎁 إنشاء عرض جديد"),
        KeyboardButton("👥 إحصائيات الأعضاء"),
        KeyboardButton("🔙 رجوع"),
    )
    return m


def back_menu():
    m = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    m.add(KeyboardButton("🔙 رجوع"))
    return m

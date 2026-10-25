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

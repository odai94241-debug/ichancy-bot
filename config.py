import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7753870725"))

AGENT_CODE = os.getenv("AGENT_CODE", "2826132-odai1@agents.nps")
ICHANCY_PANEL_URL = os.getenv("ICHANCY_PANEL_URL", "https://agents.ichancy.com")

MIN_DEPOSIT = int(os.getenv("MIN_DEPOSIT", "200"))
MIN_WITHDRAWAL = int(os.getenv("MIN_WITHDRAWAL", "500"))
MIN_USD_DEPOSIT = float(os.getenv("MIN_USD_DEPOSIT", "2.0"))

REFERRAL_PROFIT_SHARE = float(os.getenv("REFERRAL_PROFIT_SHARE", "0.05"))
REFERRAL_MIN_ACTIVE = int(os.getenv("REFERRAL_MIN_ACTIVE", "3"))

DEFAULT_USD_RATE = float(os.getenv("DEFAULT_USD_RATE", "140"))

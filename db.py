import sqlite3
from datetime import datetime

DB_PATH = "bot_data.db"


def db_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = db_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, first_name TEXT,
        balance REAL DEFAULT 0, total_deposited REAL DEFAULT 0,
        total_withdrawn REAL DEFAULT 0, referred_by INTEGER,
        created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS accounts (
        user_id INTEGER PRIMARY KEY, username TEXT, password TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        amount REAL, method TEXT, account_num TEXT,
        status TEXT DEFAULT 'pending', reason TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        amount REAL, method TEXT, tx_id TEXT,
        status TEXT DEFAULT 'pending', reason TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, percent REAL,
        start_time TEXT, end_time TEXT, active INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT)""")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance','off')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('sham_cash','غير محدد')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('syriatel_cash','غير محدد')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('herm','غير محدد')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('usd_rate','140')")
    c.execute("""INSERT OR IGNORE INTO settings VALUES ('terms',
        '⚠️ شروط الاستخدام — odai Robert\n\n'
        'عند الضغط على زر موافقة فأنت توافق على الشروط القائمة ضمن البوت.\n'
        'يرجى قراءة هذه الشروط قبل استخدام البوت.\n\n'
        'البوت مخصّص لإنشاء الحسابات، والسحب، والتعبئة الفورية لحسابات iChancy.\n\n'
        '⛔️ الشروط:\n\n'
        '1️⃣ منع الحسابات المتعددة: إنشاء أكثر من حساب للشخص الواحد مخالف للقوانين.\n\n'
        '2️⃣ تبديل طرق الدفع غير مسموح.\n\n'
        '3️⃣ شروط أرباح الإحالات: تُحتسب فقط بعد 3 إحالات نشطة.\n\n'
        '4️⃣ نسبة السحب: 10% حتى 50 مليون / 15% حتى 150 مليون / 20% أكثر.\n\n'
        '5️⃣ لا تقم بالتحويل من *3040#.\n\n'
        '6️⃣ تأكد من عنوان شام كاش قبل التحويل.\n\n'
        '7️⃣ عند التحويل من شام كاش لا ترسل ملاحظات.\n\n'
        '📌 شرط السحب مع البونص: ضعف المبلغ المشحون.\n\n'
        '⛔️ أي محاولة تحايل → إيقاف الحساب وتجميد الأرصدة.')""")
    conn.commit()
    conn.close()


def get_setting(k):
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (k,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else ""


def set_setting(k, v):
    conn = db_conn()
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key,value) VALUES (?,?)", (k, v))
    conn.commit()
    conn.close()


def add_user(uid, name, ref=None):
    conn = db_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id,first_name,referred_by,created_at) VALUES (?,?,?,?)",
              (uid, name, ref, str(datetime.now())))
    conn.commit()
    conn.close()


def get_user(uid):
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT balance,total_deposited,total_withdrawn,referred_by FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    conn.close()
    return r if r else (0, 0, 0, None)


def update_balance(uid, amt):
    conn = db_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amt, uid))
    conn.commit()
    conn.close()


def add_deposit_total(uid, amt):
    conn = db_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET total_deposited = total_deposited + ? WHERE user_id=?", (amt, uid))
    conn.commit()
    conn.close()


def add_withdraw_total(uid, amt):
    conn = db_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE user_id=?", (amt, uid))
    conn.commit()
    conn.close()


def save_account(uid, u, p):
    conn = db_conn()
    c = conn.cursor()
    c.execute("REPLACE INTO accounts VALUES (?,?,?)", (uid, u, p))
    conn.commit()
    conn.close()


def get_account(uid):
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT username,password FROM accounts WHERE user_id=?", (uid,))
    r = c.fetchone()
    conn.close()
    return r


def get_all_users():
    conn = db_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    r = c.fetchall()
    conn.close()
    return [x[0] for x in r]


def get_active_offer():
    conn = db_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("SELECT percent FROM offers WHERE active=1 AND start_time<=? AND end_time>=?", (now, now))
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

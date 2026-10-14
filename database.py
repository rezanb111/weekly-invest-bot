import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import config

DB_PATH = "bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                language TEXT DEFAULT 'fa',
                balance REAL DEFAULT 0,
                invested REAL DEFAULT 0,
                total_profit REAL DEFAULT 0,
                last_profit_date TEXT,
                referral_id INTEGER,
                referrals_count INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at TEXT,
                captcha_passed INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending',  -- pending, approved, rejected
                txid TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS profit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                percent REAL,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT
            )
        """)
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def create_user(user_id: int, username: str, full_name: str, referral_id: Optional[int] = None):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users 
               (user_id, username, full_name, referral_id, created_at, last_profit_date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username, full_name, referral_id, now, now)
        )
        if referral_id:
            await db.execute(
                "UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?",
                (referral_id,)
            )
        await db.commit()

async def update_user(user_id: int, **kwargs):
    if not kwargs:
        return
    keys = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {keys} WHERE user_id = ?", values)
        await db.commit()

async def set_captcha_passed(user_id: int):
    await update_user(user_id, captcha_passed=1)

async def set_language(user_id: int, lang: str):
    await update_user(user_id, language=lang)

async def add_deposit_request(user_id: int, amount: float, txid: str = "") -> int:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO deposits (user_id, amount, txid, created_at) VALUES (?, ?, ?, ?)",
            (user_id, amount, txid, now)
        )
        await db.commit()
        return cursor.lastrowid

async def approve_deposit(deposit_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM deposits WHERE id = ? AND status = 'pending'", (deposit_id,)) as cursor:
            dep = await cursor.fetchone()
            if not dep:
                return False
            dep = dict(dep)
        await db.execute("UPDATE deposits SET status = 'approved' WHERE id = ?", (deposit_id,))
        await db.execute(
            "UPDATE users SET invested = invested + ?, balance = balance + ? WHERE user_id = ?",
            (dep["amount"], dep["amount"], dep["user_id"])
        )
        await db.commit()
        return True

async def reject_deposit(deposit_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE deposits SET status = 'rejected' WHERE id = ? AND status = 'pending'", (deposit_id,))
        await db.commit()
        return True

async def get_pending_deposits() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM deposits WHERE status = 'pending' ORDER BY id DESC LIMIT 50") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def apply_weekly_profit(user_id: int) -> float:
    """محاسبه و اعمال سود ۵٪ هفتگی اگر ۷ روز گذشته باشد"""
    user = await get_user(user_id)
    if not user or user["invested"] <= 0:
        return 0.0

    last = user.get("last_profit_date")
    if last:
        last_dt = datetime.fromisoformat(last)
        if datetime.utcnow() - last_dt < timedelta(days=7):
            return 0.0

    profit = user["invested"] * (config.WEEKLY_PROFIT_PERCENT / 100.0)
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance = balance + ?, total_profit = total_profit + ?, last_profit_date = ? WHERE user_id = ?",
            (profit, profit, now, user_id)
        )
        await db.execute(
            "INSERT INTO profit_logs (user_id, amount, percent, created_at) VALUES (?, ?, ?, ?)",
            (user_id, profit, config.WEEKLY_PROFIT_PERCENT, now)
        )
        await db.commit()
    return profit

async def apply_profit_to_all() -> int:
    """اعمال سود به همه کاربرانی که واجد شرایط هستند (برای ادمین)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id FROM users WHERE invested > 0") as cursor:
            users = await cursor.fetchall()
    count = 0
    for u in users:
        p = await apply_weekly_profit(u["user_id"])
        if p > 0:
            count += 1
    return count

async def get_leaderboard(by: str = "invested", limit: int = 10) -> List[Dict]:
    """by: invested, balance, total_profit, referrals_count"""
    allowed = {"invested", "balance", "total_profit", "referrals_count"}
    if by not in allowed:
        by = "invested"
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT user_id, username, full_name, {by} as value FROM users WHERE is_banned = 0 ORDER BY {by} DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_stats() -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            total_users = (await c.fetchone())[0]
        async with db.execute("SELECT SUM(invested), SUM(balance), SUM(total_profit) FROM users") as c:
            row = await c.fetchone()
            total_invested = row[0] or 0
            total_balance = row[1] or 0
            total_profit = row[2] or 0
        async with db.execute("SELECT COUNT(*) FROM deposits WHERE status = 'pending'") as c:
            pending = (await c.fetchone())[0]
    return {
        "total_users": total_users,
        "total_invested": total_invested,
        "total_balance": total_balance,
        "total_profit": total_profit,
        "pending_deposits": pending,
    }

async def add_support_message(user_id: int, message: str):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO support_messages (user_id, message, created_at) VALUES (?, ?, ?)",
            (user_id, message, now)
        )
        await db.commit()

async def get_open_supports(limit: int = 20) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM support_messages WHERE status = 'open' ORDER BY id DESC LIMIT ?",
            (limit,)
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

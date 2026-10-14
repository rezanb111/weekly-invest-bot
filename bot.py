import asyncio
import random
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
import database as db
import keyboards as kb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


# ==================== States ====================
class InvestStates(StatesGroup):
    waiting_amount = State()
    waiting_txid = State()

class SupportStates(StatesGroup):
    waiting_message = State()

class BroadcastStates(StatesGroup):
    waiting_text = State()

class CaptchaStates(StatesGroup):
    waiting = State()


# ==================== Helpers ====================
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

def get_text(lang: str, key: str, **kwargs) -> str:
    texts = config.TEXTS.get(lang, config.TEXTS["fa"])
    text = texts.get(key, key)
    try:
        return text.format(**kwargs)
    except Exception:
        return text

async def ensure_user(message_or_cb, state: FSMContext = None):
    user = message_or_cb.from_user
    existing = await db.get_user(user.id)
    if not existing:
        ref = None
        if isinstance(message_or_cb, Message) and message_or_cb.text and message_or_cb.text.startswith("/start "):
            try:
                ref = int(message_or_cb.text.split()[1])
                if ref == user.id:
                    ref = None
            except Exception:
                ref = None
        await db.create_user(user.id, user.username or "", user.full_name or "", ref)
        existing = await db.get_user(user.id)
    return existing


# ==================== Captcha ====================
def generate_captcha():
    a = random.randint(1, 15)
    b = random.randint(1, 10)
    answer = a + b
    options = [answer]
    while len(options) < 6:
        wrong = answer + random.randint(-10, 10)
        if wrong != answer and wrong > 0 and wrong not in options:
            options.append(wrong)
    random.shuffle(options)
    return f"{a} + {b} = ?", answer, options


# ==================== Start & Captcha ====================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject = None):
    await state.clear()
    user = await ensure_user(message)

    if user.get("captcha_passed"):
        lang = user.get("language", "fa")
        await show_main_menu(message, user)
        return

    # تولید کپچا
    question, answer, options = generate_captcha()
    await state.set_state(CaptchaStates.waiting)
    await state.update_data(captcha_answer=answer)

    lang = user.get("language", "fa")
    text = get_text(lang, "start", name=message.from_user.first_name or "کاربر")
    text += f"\n\n🔐 <b>{question}</b>"
    await message.answer(text, reply_markup=kb.captcha_keyboard(options))


@dp.callback_query(F.data.startswith("captcha:"), CaptchaStates.waiting)
async def process_captcha(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    correct = data.get("captcha_answer")
    chosen = int(callback.data.split(":")[1])

    user = await db.get_user(callback.from_user.id)
    lang = user.get("language", "fa") if user else "fa"

    if chosen == correct:
        await db.set_captcha_passed(callback.from_user.id)
        await state.clear()
        await callback.message.edit_text(get_text(lang, "captcha_ok"))
        user = await db.get_user(callback.from_user.id)
        await show_main_menu(callback.message, user, edit=False)
    else:
        # کپچای جدید
        question, answer, options = generate_captcha()
        await state.update_data(captcha_answer=answer)
        await callback.message.edit_text(
            get_text(lang, "captcha_wrong") + f"\n\n🔐 <b>{question}</b>",
            reply_markup=kb.captcha_keyboard(options)
        )
    await callback.answer()


# ==================== Main Menu ====================
async def show_main_menu(target, user, edit: bool = False):
    lang = user.get("language", "fa")
    # اعمال سود هفتگی اگر موقعش رسیده
    profit = await db.apply_weekly_profit(user["user_id"])
    if profit > 0:
        extra = f"\n\n🎉 <b>سود هفتگی شما واریز شد: +{profit:.2f}</b>"
    else:
        extra = ""

    user = await db.get_user(user["user_id"])  # رفرش
    text = get_text(
        lang, "main_menu",
        balance=user["balance"],
        invested=user["invested"],
        total_profit=user["total_profit"]
    ) + extra

    markup = kb.main_menu_keyboard(lang, is_admin=is_admin(user["user_id"]))
    if edit and hasattr(target, "edit_text"):
        try:
            await target.edit_text(text, reply_markup=markup)
        except Exception:
            await target.answer(text, reply_markup=markup)
    else:
        if hasattr(target, "answer"):
            await target.answer(text, reply_markup=markup)
        else:
            await bot.send_message(target.chat.id, text, reply_markup=markup)


@dp.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await db.get_user(callback.from_user.id)
    if not user or not user.get("captcha_passed"):
        await callback.answer("اول کپچا رو حل کن", show_alert=True)
        return
    await show_main_menu(callback.message, user, edit=True)
    await callback.answer()


# ==================== Invest ====================
@dp.callback_query(F.data == "menu:invest")
async def cb_invest(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    if not user or not user.get("captcha_passed"):
        await callback.answer("اول کپچا رو حل کن", show_alert=True)
        return
    lang = user.get("language", "fa")
    text = get_text(lang, "invest", min_amount=config.MIN_INVEST_AMOUNT)
    await state.set_state(InvestStates.waiting_amount)
    await callback.message.edit_text(text, reply_markup=kb.back_keyboard())
    await callback.answer()


@dp.message(InvestStates.waiting_amount)
async def process_invest_amount(message: Message, state: FSMContext):
    if message.text and message.text.strip() in ["❌ لغو / Cancel", "❌ لغو", "Cancel"]:
        await state.clear()
        user = await db.get_user(message.from_user.id)
        await show_main_menu(message, user)
        return

    try:
        amount = float(message.text.strip().replace(",", ""))
        if amount < config.MIN_INVEST_AMOUNT:
            await message.answer(f"❌ حداقل مبلغ {config.MIN_INVEST_AMOUNT} است. دوباره بفرست:")
            return
    except Exception:
        await message.answer("❌ لطفاً فقط عدد بفرست (مثلاً 50 یا 100.5)")
        return

    await state.update_data(invest_amount=amount)
    await state.set_state(InvestStates.waiting_txid)
    await message.answer(
        f"✅ مبلغ {amount} ثبت شد.\n\n"
        "حالا TXID یا هش تراکنش رو بفرست (یا بنویس «ندارم» تا فقط درخواست ثبت بشه):",
        reply_markup=kb.cancel_keyboard()
    )


@dp.message(InvestStates.waiting_txid)
async def process_invest_txid(message: Message, state: FSMContext):
    if message.text and message.text.strip() in ["❌ لغو / Cancel", "❌ لغو", "Cancel"]:
        await state.clear()
        user = await db.get_user(message.from_user.id)
        await show_main_menu(message, user)
        return

    data = await state.get_data()
    amount = data.get("invest_amount", 0)
    txid = message.text.strip() if message.text else ""

    dep_id = await db.add_deposit_request(message.from_user.id, amount, txid)
    await state.clear()

    user = await db.get_user(message.from_user.id)
    lang = user.get("language", "fa")
    await message.answer(
        get_text(lang, "invest_success", amount=amount) + f"\n\nشماره درخواست: #{dep_id}",
        reply_markup=kb.back_keyboard()
    )

    # اطلاع به ادمین‌ها
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📥 درخواست سرمایه‌گذاری جدید\n\n"
                f"کاربر: {message.from_user.full_name} (@{message.from_user.username})\n"
                f"آیدی: <code>{message.from_user.id}</code>\n"
                f"مبلغ: <b>{amount}</b>\n"
                f"TXID: <code>{txid}</code>\n"
                f"شماره: #{dep_id}",
                reply_markup=kb.deposit_actions_keyboard(dep_id)
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


# ==================== Balance ====================
@dp.callback_query(F.data == "menu:balance")
async def cb_balance(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("خطا", show_alert=True)
        return
    # چک سود
    await db.apply_weekly_profit(user["user_id"])
    user = await db.get_user(callback.from_user.id)
    lang = user.get("language", "fa")
    text = get_text(lang, "balance", balance=user["balance"], invested=user["invested"], total_profit=user["total_profit"])
    await callback.message.edit_text(text, reply_markup=kb.back_keyboard())
    await callback.answer()


# ==================== Leaderboard ====================
@dp.callback_query(F.data == "menu:leaderboard")
async def cb_leaderboard_menu(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    lang = user.get("language", "fa") if user else "fa"
    text = get_text(lang, "leaderboard")
    await callback.message.edit_text(text, reply_markup=kb.leaderboard_keyboard(lang))
    await callback.answer()


@dp.callback_query(F.data.startswith("lb:"))
async def cb_leaderboard_show(callback: CallbackQuery):
    by = callback.data.split(":")[1]
    titles = {
        "invested": "💰 بیشترین سرمایه‌گذاری",
        "balance": "💳 بیشترین موجودی",
        "total_profit": "📈 بیشترین سود",
        "referrals_count": "👥 بیشترین دعوت",
    }
    rows = await db.get_leaderboard(by=by, limit=10)
    text = f"<b>{titles.get(by, 'لیدربورد')}</b>\n\n"
    if not rows:
        text += "هنوز کسی نیست."
    else:
        medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
        for i, r in enumerate(rows):
            name = r.get("full_name") or r.get("username") or str(r["user_id"])
            text += f"{medals[i]} <b>{i+1}.</b> {name[:20]} — <code>{r['value']:.2f}</code>\n"
    await callback.message.edit_text(text, reply_markup=kb.leaderboard_keyboard())
    await callback.answer()


# ==================== Support ====================
@dp.callback_query(F.data == "menu:support")
async def cb_support(callback: CallbackQuery, state: FSMContext):
    user = await db.get_user(callback.from_user.id)
    lang = user.get("language", "fa") if user else "fa"
    text = get_text(lang, "support", support=config.SUPPORT_USERNAME)
    await state.set_state(SupportStates.waiting_message)
    await callback.message.edit_text(text + "\n\nپیام خودت رو بنویس:", reply_markup=kb.back_keyboard())
    await callback.answer()


@dp.message(SupportStates.waiting_message)
async def process_support(message: Message, state: FSMContext):
    if message.text and message.text.strip() in ["❌ لغو / Cancel", "❌ لغو", "Cancel", "🔙 بازگشت"]:
        await state.clear()
        user = await db.get_user(message.from_user.id)
        await show_main_menu(message, user)
        return

    text = message.text or (message.caption or "")
    if not text:
        await message.answer("لطفاً متن پیام بفرست.")
        return

    await db.add_support_message(message.from_user.id, text)
    await state.clear()
    await message.answer("✅ پیام شما به پشتیبانی ارسال شد. به زودی پاسخ می‌دهیم.", reply_markup=kb.back_keyboard())

    # به ادمین
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📩 پیام پشتیبانی جدید\n\n"
                f"از: {message.from_user.full_name} (@{message.from_user.username})\n"
                f"آیدی: <code>{message.from_user.id}</code>\n\n"
                f"{text}"
            )
        except Exception:
            pass


# ==================== Referral ====================
@dp.callback_query(F.data == "menu:referral")
async def cb_referral(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("خطا", show_alert=True)
        return
    lang = user.get("language", "fa")
    me = await bot.get_me()
    text = get_text(
        lang, "referral",
        bot_username=me.username,
        user_id=user["user_id"],
        refs=user.get("referrals_count", 0)
    )
    await callback.message.edit_text(text, reply_markup=kb.back_keyboard())
    await callback.answer()


# ==================== Language ====================
@dp.callback_query(F.data == "menu:language")
async def cb_language(callback: CallbackQuery):
    await callback.message.edit_text("🌐 زبان خود را انتخاب کنید / Select Language:", reply_markup=kb.language_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("lang:"))
async def cb_set_language(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    if lang not in config.LANGUAGES:
        await callback.answer("Invalid", show_alert=True)
        return
    await db.set_language(callback.from_user.id, lang)
    await callback.answer("✅ Language changed!" if lang == "en" else "✅ زبان تغییر کرد!")
    user = await db.get_user(callback.from_user.id)
    await show_main_menu(callback.message, user, edit=True)


# ==================== Profit Info ====================
@dp.callback_query(F.data == "menu:profit_info")
async def cb_profit_info(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    lang = user.get("language", "fa") if user else "fa"
    text = get_text(lang, "weekly_profit_info", percent=config.WEEKLY_PROFIT_PERCENT)
    text += "\n\nسود به صورت خودکار هر ۷ روز یکبار به موجودی شما اضافه می‌شود."
    await callback.message.edit_text(text, reply_markup=kb.back_keyboard())
    await callback.answer()


# ==================== Admin Panel ====================
@dp.callback_query(F.data == "menu:admin")
async def cb_admin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(get_text("fa", "no_access"), show_alert=True)
        return
    await callback.message.edit_text("🛠 <b>پنل مدیریت</b>\n\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=kb.admin_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("No access", show_alert=True)
        return
    stats = await db.get_stats()
    text = (
        "📊 <b>آمار کلی ربات</b>\n\n"
        f"👥 تعداد کاربران: <b>{stats['total_users']}</b>\n"
        f"💰 کل سرمایه‌گذاری شده: <b>{stats['total_invested']:.2f}</b>\n"
        f"💳 کل موجودی‌ها: <b>{stats['total_balance']:.2f}</b>\n"
        f"📈 کل سود پرداختی: <b>{stats['total_profit']:.2f}</b>\n"
        f"⏳ واریزهای در انتظار: <b>{stats['pending_deposits']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=kb.admin_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "admin:pending")
async def admin_pending(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("No access", show_alert=True)
        return
    pending = await db.get_pending_deposits()
    if not pending:
        await callback.message.edit_text("✅ هیچ واریز در انتظاری نیست.", reply_markup=kb.admin_keyboard())
        await callback.answer()
        return

    for dep in pending[:10]:  # حداکثر ۱۰ تا
        user = await db.get_user(dep["user_id"])
        name = user.get("full_name") if user else str(dep["user_id"])
        text = (
            f"📥 درخواست #{dep['id']}\n"
            f"کاربر: {name} (<code>{dep['user_id']}</code>)\n"
            f"مبلغ: <b>{dep['amount']}</b>\n"
            f"TXID: <code>{dep['txid'] or '—'}</code>\n"
            f"زمان: {dep['created_at'][:16]}"
        )
        await callback.message.answer(text, reply_markup=kb.deposit_actions_keyboard(dep["id"]))
    await callback.answer()


@dp.callback_query(F.data.startswith("dep:approve:"))
async def dep_approve(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("No access", show_alert=True)
        return
    dep_id = int(callback.data.split(":")[2])
    # گرفتن اطلاعات قبل از تایید
    import aiosqlite
    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM deposits WHERE id = ?", (dep_id,)) as cur:
            dep_row = await cur.fetchone()
    ok = await db.approve_deposit(dep_id)
    if ok and dep_row:
        await callback.message.edit_text(callback.message.text + "\n\n✅ <b>تایید شد</b>")
        try:
            await bot.send_message(
                dep_row["user_id"],
                f"✅ درخواست سرمایه‌گذاری شما به مبلغ <b>{dep_row['amount']}</b> تایید شد!\n"
                f"مبلغ به موجودی و سرمایه‌گذاری شما اضافه گردید."
            )
        except Exception:
            pass
        await callback.answer("✅ تایید شد")
    else:
        await callback.answer("قبلاً پردازش شده یا پیدا نشد", show_alert=True)


@dp.callback_query(F.data.startswith("dep:reject:"))
async def dep_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("No access", show_alert=True)
        return
    dep_id = int(callback.data.split(":")[2])
    ok = await db.reject_deposit(dep_id)
    if ok:
        await callback.message.edit_text(callback.message.text + "\n\n❌ <b>رد شد</b>")
        await callback.answer("رد شد")
    else:
        await callback.answer("قبلاً پردازش شده", show_alert=True)


@dp.callback_query(F.data == "admin:apply_profit")
async def admin_apply_profit(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("No access", show_alert=True)
        return
    await callback.answer("در حال اعمال سود...")
    count = await db.apply_profit_to_all()
    await callback.message.edit_text(
        f"✅ سود هفتگی به <b>{count}</b> کاربر واجد شرایط اعمال شد.",
        reply_markup=kb.admin_keyboard()
    )


@dp.callback_query(F.data == "admin:supports")
async def admin_supports(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("No access", show_alert=True)
        return
    msgs = await db.get_open_supports(15)
    if not msgs:
        await callback.message.edit_text("✅ هیچ پیام پشتیبانی بازی نیست.", reply_markup=kb.admin_keyboard())
        await callback.answer()
        return
    text = "📩 <b>پیام‌های پشتیبانی اخیر:</b>\n\n"
    for m in msgs:
        text += f"#{m['id']} | کاربر <code>{m['user_id']}</code>\n{m['message'][:80]}...\n\n"
    await callback.message.edit_text(text, reply_markup=kb.admin_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("No access", show_alert=True)
        return
    await state.set_state(BroadcastStates.waiting_text)
    await callback.message.edit_text("📢 متن پیام همگانی را بفرستید:\n(برای لغو /cancel)", reply_markup=kb.back_keyboard())
    await callback.answer()


@dp.message(BroadcastStates.waiting_text)
async def process_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer("لغو شد.")
        return

    text = message.text or message.caption or ""
    await state.clear()
    await message.answer("⏳ در حال ارسال...")

    # ارسال به همه
    import aiosqlite
    async with aiosqlite.connect(db.DB_PATH) as conn:
        async with conn.execute("SELECT user_id FROM users WHERE is_banned = 0") as cursor:
            users = await cursor.fetchall()

    success = 0
    fail = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, f"📢 <b>پیام از مدیریت:</b>\n\n{text}")
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
    await message.answer(f"✅ ارسال تمام شد.\nموفق: {success}\nناموفق: {fail}")


# ==================== Fallback ====================
@dp.message()
async def fallback(message: Message, state: FSMContext):
    current = await state.get_state()
    if current:
        return  # در حال انجام عملیاتی است
    user = await db.get_user(message.from_user.id)
    if user and user.get("captcha_passed"):
        await show_main_menu(message, user)
    else:
        await message.answer("لطفاً /start را بزنید.")


# ==================== Main ====================
async def main():
    await db.init_db()
    logger.info("Database initialized")
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

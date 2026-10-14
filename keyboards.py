from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import config

def captcha_keyboard(options: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(text=str(opt), callback_data=f"captcha:{opt}")
    builder.adjust(3)
    return builder.as_markup()

def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, name in config.LANGUAGES.items():
        builder.button(text=name, callback_data=f"lang:{code}")
    builder.adjust(2)
    return builder.as_markup()

def main_menu_keyboard(lang: str = "fa", is_admin: bool = False) -> InlineKeyboardMarkup:
    t = config.TEXTS.get(lang, config.TEXTS["fa"])
    builder = InlineKeyboardBuilder()
    
    # دکمه‌های رنگی با ایموجی
    builder.button(text="💰 سرمایه‌گذاری / Invest", callback_data="menu:invest")
    builder.button(text="💳 موجودی من / Balance", callback_data="menu:balance")
    builder.button(text="🏆 لیدربورد / Leaderboard", callback_data="menu:leaderboard")
    builder.button(text="📞 پشتیبانی / Support", callback_data="menu:support")
    builder.button(text="🔗 دعوت دوستان / Referral", callback_data="menu:referral")
    builder.button(text="🌐 تغییر زبان / Language", callback_data="menu:language")
    builder.button(text="📈 اطلاعات سود هفتگی", callback_data="menu:profit_info")
    
    if is_admin:
        builder.button(text="🛠 پنل ادمین / Admin", callback_data="menu:admin")
    
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()

def leaderboard_keyboard(lang: str = "fa") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 بیشترین سرمایه‌گذاری", callback_data="lb:invested")
    builder.button(text="💳 بیشترین موجودی", callback_data="lb:balance")
    builder.button(text="📈 بیشترین سود", callback_data="lb:total_profit")
    builder.button(text="👥 بیشترین دعوت", callback_data="lb:referrals_count")
    builder.button(text="🔙 بازگشت", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()

def admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # دکمه‌های رنگی ادمین
    builder.button(text="📊 آمار کلی", callback_data="admin:stats")
    builder.button(text="⏳ واریزهای در انتظار", callback_data="admin:pending")
    builder.button(text="💰 اعمال سود هفتگی به همه", callback_data="admin:apply_profit")
    builder.button(text="📩 پیام‌های پشتیبانی", callback_data="admin:supports")
    builder.button(text="📢 ارسال همگانی", callback_data="admin:broadcast")
    builder.button(text="🔙 بازگشت به منو", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()

def deposit_actions_keyboard(deposit_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ تایید", callback_data=f"dep:approve:{deposit_id}")
    builder.button(text="❌ رد", callback_data=f"dep:reject:{deposit_id}")
    builder.adjust(2)
    return builder.as_markup()

def back_keyboard(callback: str = "menu:main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 بازگشت", callback_data=callback)
    return builder.as_markup()

def cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ لغو / Cancel")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

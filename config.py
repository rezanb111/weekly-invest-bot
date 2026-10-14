import os
from dotenv import load_dotenv

load_dotenv()

# ==================== تنظیمات اصلی ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ادمین‌ها - یوزرنیم (بدون @)
ADMIN_IDS = ["marcenzo", "shibainuo"]

# درصد سود هفتگی
WEEKLY_PROFIT_PERCENT = 5.0

# حداقل مبلغ سرمایه‌گذاری
MIN_INVEST_AMOUNT = 10

# حداقل مبلغ وام (با ضمانت)
MIN_LOAN_AMOUNT = 200

# پشتیبانی
SUPPORT_USERNAME = "@YourSupport"

LANGUAGES = {
    "fa": "🇮🇷 فارسی",
    "en": "🇬🇧 English",
}

TEXTS = {
    "fa": {
        "start": "سلام {name} عزیز 👋\nبه ربات سرمایه‌گذاری هفتگی خوش اومدی!\n\n💰 هر هفته ۵٪ سود روی سرمایه‌ات دریافت کن\n🏆 در لیدربورد شرکت کن و رتبه بگیری\n💳 وام با ضمانت برای مبالغ بالای ۲۰۰ دلار\n\nاول کپچا رو حل کن:",
        "captcha_wrong": "❌ کپچا اشتباه بود. دوباره تلاش کن:",
        "captcha_ok": "✅ کپچا تایید شد!",
        "main_menu": "🏠 منوی اصلی\n\nموجودی: {balance:.2f}\nسرمایه‌گذاری شده: {invested:.2f}\nقفل‌شده (ضمانت): {locked:.2f}\nسود کل: {total_profit:.2f}",
        "invest": "💰 سرمایه‌گذاری\n\nحداقل مبلغ: {min_amount}\n\nمبلغ مورد نظر رو به صورت عدد بفرست (مثلاً 100)",
        "invest_success": "✅ درخواست سرمایه‌گذاری به مبلغ {amount} ثبت شد.\nلطفاً به ادمین اطلاع بده یا TXID بفرست.",
        "support": "📞 پشتیبانی\n\nبرای ارتباط با پشتیبانی پیام خودت رو بفرست.\nیا به {support} پیام بده.",
        "leaderboard": "🏆 لیدربورد\n\nانتخاب کن کدوم بخش رو می‌خوای ببینی:",
        "language": "🌐 انتخاب زبان",
        "admin_panel": "🛠 پنل ادمین",
        "no_access": "❌ دسترسی نداری.",
        "balance": "💳 موجودی من\n\nموجودی قابل برداشت: {balance:.2f}\nسرمایه‌گذاری شده: {invested:.2f}\nقفل‌شده برای ضمانت: {locked:.2f}\nسود کل دریافتی: {total_profit:.2f}",
        "weekly_profit_info": "📈 سود هفتگی: {percent}% روی مبلغ سرمایه‌گذاری شده\nهر ۷ روز یکبار محاسبه می‌شه.",
        "referral": "🔗 لینک دعوت تو:\nhttps://t.me/{bot_username}?start={user_id}\n\nدعوت‌شده‌ها: {refs}",
        "loan_info": "💳 وام با ضمانت\n\nکاربرانی که در ربات سرمایه‌گذاری کرده‌اند می‌توانند به همان میزان سرمایه‌گذاری‌شان ضمانت فردی کنند.\n\nفرد وام‌گیرنده برای مبالغ بالای {min_loan} دلار می‌تواند وام بگیرد.\nوجوه ضامن‌ها تا تسویه کامل اقساط در ربات قفل می‌شود.\n\nحداقل مبلغ وام: {min_loan} دلار",
        "back": "🔙 بازگشت",
        "cancel": "❌ لغو",
    },
    "en": {
        "start": "Hello {name} 👋\nWelcome to the Weekly Investment Bot!\n\n💰 Get 5% profit every week on your capital\n🏆 Compete in the leaderboard\n💳 Guaranteed Loan for amounts over $200\n\nFirst solve the captcha:",
        "captcha_wrong": "❌ Wrong captcha. Try again:",
        "captcha_ok": "✅ Captcha verified!",
        "main_menu": "🏠 Main Menu\n\nBalance: {balance:.2f}\nInvested: {invested:.2f}\nLocked (Guarantee): {locked:.2f}\nTotal Profit: {total_profit:.2f}",
        "invest": "💰 Invest\n\nMinimum amount: {min_amount}\n\nSend the amount as a number (e.g. 100)",
        "invest_success": "✅ Investment request of {amount} registered.\nPlease contact admin or send TXID.",
        "support": "📞 Support\n\nSend your message for support.\nOr contact {support}",
        "leaderboard": "🏆 Leaderboard\n\nChoose which section you want to see:",
        "language": "🌐 Select Language",
        "admin_panel": "🛠 Admin Panel",
        "no_access": "❌ Access denied.",
        "balance": "💳 My Balance\n\nWithdrawable: {balance:.2f}\nInvested: {invested:.2f}\nLocked for Guarantee: {locked:.2f}\nTotal Profit: {total_profit:.2f}",
        "weekly_profit_info": "📈 Weekly Profit: {percent}% on invested amount\nCalculated every 7 days.",
        "referral": "🔗 Your referral link:\nhttps://t.me/{bot_username}?start={user_id}\n\nReferrals: {refs}",
        "loan_info": "💳 Guaranteed Loan\n\nUsers who invest can guarantee others up to their invested amount.\n\nBorrower can take loan over ${min_loan}.\nGuarantors' funds stay locked until full repayment.\n\nMinimum loan: ${min_loan}",
        "back": "🔙 Back",
        "cancel": "❌ Cancel",
    },
}

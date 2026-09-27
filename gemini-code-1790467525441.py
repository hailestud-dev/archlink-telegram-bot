import os
import logging
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ConversationHandler, ContextTypes
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

ROLE_CHOICE, REG_NAME, REG_SKILLS, REG_PORTFOLIO, POST_JOB_TITLE, POST_JOB_DESC, POST_JOB_BUDGET, BID_PRICE, BID_DAYS = range(9)

def get_db():
    return sqlite3.connect('archlink.db')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT role, full_name FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        role, name = user
        if role == 'architect':
            keyboard = [['🔍 አዳዲስ ስራዎችን እይ'], ['👤 ፕሮፋይል ማስተካከያ']]
        else:
            keyboard = [['➕ አዲስ ስራ ልጠፍ'], ['📋 የለቀቅኳቸውን ስራዎች እይ']]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(f"እንኳን በደህና መጡ **{name}**! 👋\nእንደ **{role.capitalize()}** ገብተዋል።", reply_markup=reply_markup)
        return ConversationHandler.END
    else:
        keyboard = [['📐 አርክቴክት/ፍሪላንሰር ነኝ'], ['🏢 አማካሪ ድርጅት (Consulting Firm) ነኝ']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("እንኳን ወደ ArchLink Ethiopia በደህና መጡ! 👋\nእባክዎን ሚናዎን ይምረጡ፡", reply_markup=reply_markup)
        return ROLE_CHOICE

async def role_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['role'] = 'architect' if 'አርክቴክት' in text else 'firm'
    await update.message.reply_text("እባክዎን ሙሉ ስምዎን ወይም የድርጅትዎን ስም ያስገቡ፡", reply_markup=ReplyKeyboardRemove())
    return REG_NAME

async def name_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    if context.user_data['role'] == 'architect':
        await update.message.reply_text("የሚያውቋቸውን ሶፍትዌሮች ያስገቡ (ምሳሌ: AutoCAD, Revit, 3D Max):")
        return REG_SKILLS
    else:
        return await save_user(update, context, skills="N/A", portfolio="N/A")

async def skills_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['skills'] = update.message.text
    await update.message.reply_text("የፖርትፎሊዮ ሊንክ ያስገቡ፡")
    return REG_PORTFOLIO

async def portfolio_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    portfolio = update.message.text
    return await save_user(update, context, skills=context.user_data['skills'], portfolio=portfolio)

async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE, skills, portfolio):
    user_id = update.message.from_user.id
    name = context.user_data['name']
    role = context.user_data['role']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, full_name, role, skills) VALUES (?, ?, ?, ?)",
        (user_id, name, role, skills)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("ምዝገባዎ በስኬት ተጠናቋል! 🎉 /start ን በመጫን ዳሽቦርድዎን ያግኙ።")
    return ConversationHandler.END

async def start_post_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("የስራውን ርዕስ ያስገቡ (ምሳሌ: G+2 Architectural Drafting):")
    return POST_JOB_TITLE

async def job_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['job_title'] = update.message.text
    await update.message.reply_text("የስራውን ዝርዝር መግለጫ ያስገቡ፡")
    return POST_JOB_DESC

async def job_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['job_desc'] = update.message.text
    await update.message.reply_text("ለዚህ ስራ የተመደበውን በጀት ያስገቡ (በ ETB):")
    return POST_JOB_BUDGET

async def job_budget_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    budget = update.message.text
    firm_id = update.message.from_user.id
    title = context.user_data['job_title']
    desc = context.user_data['job_desc']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs (firm_id, title, description, budget) VALUES (?, ?, ?, ?)", (firm_id, title, desc, budget))
    conn.commit()
    conn.close()

    await update.message.reply_text("ስራው በስኬት ተለጥፏል! 🚀")
    return ConversationHandler.END

async def view_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT job_id, title, description, budget FROM jobs WHERE status = 'OPEN' ORDER BY job_id DESC LIMIT 5")
    jobs = cursor.fetchall()
    conn.close()

    if not jobs:
        await update.message.reply_text("በአሁኑ ሰዓት ክፍት የሆኑ ስራዎች የሉም።")
        return

    for job in jobs:
        job_id, title, desc, budget = job
        text = f"📌 **{title}**\n\n📝 {desc}\n\n💰 **በጀት:** {budget} ETB"
        keyboard = [[InlineKeyboardButton("📩 አመልክት (Bid)", callback_data=f"bid_{job_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def bid_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    job_id = query.data.split("_")[1]
    context.user_data['bidding_job_id'] = job_id
    await query.message.reply_text("ለዚህ ስራ የሚጠይቁትን ዋጋ (በ ETB) ያስገቡ፡")
    return BID_PRICE

async def bid_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bid_price'] = update.message.text
    await update.message.reply_text("ስራውን ለማጠናቀቅ የሚወስድብዎትን ጊዜ (በቀናት) ያስገቡ፡")
    return BID_DAYS

async def bid_days_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = update.message.text
    price = context.user_data['bid_price']
    job_id = context.user_data['bidding_job_id']
    architect_id = update.message.from_user.id

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bids (job_id, architect_id, proposal_price, delivery_days) VALUES (?, ?, ?, ?)", (job_id, architect_id, price, days))
    cursor.execute("SELECT firm_id, title FROM jobs WHERE job_id = ?", (job_id,))
    job_info = cursor.fetchone()
    conn.close()

    await update.message.reply_text("ማመልከቻዎ በስኬት ተልኳል! 👍")

    if job_info:
        firm_id, job_title = job_info
        try:
            await context.bot.send_message(chat_id=firm_id, text=f"🔔 **አዲስ ማመልከቻ!**\n\nለስራዎ: **{job_title}**\n💰 ዋጋ: {price} ETB\n⏱ ጊዜ: {days} ቀን")
        except Exception as e:
            logging.error(f"Error notifying firm: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("እርምጃው ተሰርዟል።", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    from database import init_db
    init_db()

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is missing!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    registration_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ROLE_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, role_chosen)],
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_registered)],
            REG_SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, skills_registered)],
            REG_PORTFOLIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, portfolio_registered)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    job_post_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^➕ አዲስ ስራ ልጠፍ$'), start_post_job)],
        states={
            POST_JOB_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, job_title_received)],
            POST_JOB_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, job_desc_received)],
            POST_JOB_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, job_budget_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    bid_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(bid_button_click, pattern='^bid_')],
        states={
            BID_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bid_price_received)],
            BID_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, bid_days_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(registration_handler)
    app.add_handler(job_post_handler)
    app.add_handler(bid_handler)
    app.add_handler(MessageHandler(filters.Regex('^🔍 አዳዲስ ስራዎችን እይ$'), view_jobs))

    print("Bot starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
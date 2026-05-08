import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from src.agent import ask_agent

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

WELCOME = (
    "नमस्कार! 🌱 I'm KrishiMitra, your pomegranate mandi advisor.\n\n"
    "Ask me anything like:\n"
    "• 'Should I sell today?'\n"
    "• 'आज भाव काय आहे?' (What's today's price?)\n"
    "• 'Compare mandis'\n"
    "• 'Solapur trend last 14 days'\n"
)


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME)


async def handle_message(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text
    log.info("Q: %s", user_query)
    await update.message.chat.send_action("typing")

    try:
        result = ask_agent(user_query)
        rec = result["recommendation"]

        reply = (
            f"📊 Recommendation: {rec['action']}\n"
            f"🏪 Mandi: {rec['recommended_mandi']}\n"
            f"🎯 Confidence: {rec['confidence']}\n\n"
            f"🇬🇧 {rec['reasoning_english']}\n\n"
            f"🇮🇳 {rec['reasoning_marathi']}\n\n"
            f"📈 Numbers: {rec['key_numbers']}"
        )
        await update.message.reply_text(reply)
    except Exception as e:
        log.exception("Agent failed")
        await update.message.reply_text(
            f"Sorry, something went wrong: {e}\n"
            "(In production this would gracefully fall back — see README failure modes.)"
        )


def run_bot():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Bot starting…")
    app.run_polling()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_bot()
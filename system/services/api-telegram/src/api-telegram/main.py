import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()

# TOKEN do Bot do Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

API_URL = "http://localhost:8003/chat"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Sou um bot para cultivo hidropônico. Me envie sua pergunta.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_response = requests.get(API_URL, params={"string": user_message})

    if chat_response.status_code == 200:
        response_text = chat_response.json().get("response", "Desculpe, não consegui gerar uma resposta.")
    else:
        response_text = "Erro ao conectar com o chatbot."

    await update.message.reply_text(response_text)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()

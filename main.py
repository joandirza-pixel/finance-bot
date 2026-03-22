import os
import json
from datetime import datetime

import telebot
import gspread
from google.oauth2.service_account import Credentials

# ================= TELEGRAM =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# ================= GOOGLE SHEETS =================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

client_sheets = gspread.authorize(creds)
sheet = client_sheets.open("1Jgrc4lmYveqNt5ydVT5xGhyAAyrQyY-yWls5xAEscoM").sheet1

# ================= BOT =================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🤖 Finance bot ready! Send: Spent 20k on food")

@bot.message_handler(func=lambda message: True)
def handle(message):
    text = message.text.lower()

    try:
        if "spent" in text:
            t = "Expense"
        elif "earned" in text or "income" in text:
            t = "Income"
        else:
            bot.reply_to(message, "❌ Use 'Spent' or 'Earned'")
            return

        import re
        amount = int(re.search(r"\d+", text).group())

        if "food" in text:
            category = "Food"
        else:
            category = "Other"

        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            t,
            amount,
            category,
            text
        ])

        bot.reply_to(message, f"✅ Saved: {t} Rp{amount} ({category})")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ================= RUN =================
print("Bot running...")
bot.infinity_polling()

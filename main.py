import os
import json
import re
from datetime import datetime

import telebot
import gspread
from google.oauth2.service_account import Credentials

# ================== TELEGRAM SETUP ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# ================== GOOGLE SHEETS SETUP ==================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

client_sheets = gspread.authorize(creds)
sheet = client_sheets.open("Finance Tracker").sheet1

# ================== HELPER FUNCTION ==================
def parse_message(text):
    text = text.lower()

    if "spent" in text:
        t = "Expense"
    elif "earned" in text or "income" in text:
        t = "Income"
    else:
        return None

    # get number
    amount_match = re.search(r"\d+", text)
    if not amount_match:
        return None
    amount = int(amount_match.group())

    # simple category detection
    if "food" in text:
        category = "Food"
    elif "transport" in text:
        category = "Transport"
    elif "game" in text:
        category = "Gaming"
    else:
        category = "Other"

    note = text

    return t, amount, category, note

# ================== BOT HANDLER ==================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    result = parse_message(message.text)

    if not result:
        bot.reply_to(message, "❌ Format salah. Coba: 'Spent 20k on food'")
        return

    t, amount, category, note = result

    try:
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            t,
            amount,
            category,
            note
        ])

        bot.reply_to(message, f"✅ Tersimpan: {t} Rp{amount} ({category})")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ================== START BOT ==================
print("Bot is running...")
bot.infinity_polling()

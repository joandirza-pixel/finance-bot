import os
import json
import re
from datetime import datetime

import telebot
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI

# ================= TELEGRAM =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# ================= OPENAI =================
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ================= GOOGLE SHEETS =================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

client_sheets = gspread.authorize(creds)
sheet = client_sheets.open_by_key("1Jgrc4lmYveqNt5ydVT5xGhyAAyrQyY-yWls5xAEscoM").sheet1

# ================= FALLBACK PARSER =================
def fallback_parse(text):
    text_lower = text.lower()

    # type
    if any(w in text_lower for w in ["bought", "spent", "paid"]):
        t = "Expense"
    elif any(w in text_lower for w in ["got", "earned", "received"]):
        t = "Income"
    else:
        t = "Expense"

    # amount
    number = 0
    match = re.search(r"\d+", text_lower)

    if match:
        number = int(match.group())

        if "thousand" in text_lower:
            number *= 1000
        if "k" in text_lower:
            number *= 1000

    # category
    if "food" in text_lower or "snack" in text_lower:
        category = "Food"
    elif "transport" in text_lower:
        category = "Transport"
    else:
        category = "Other"

    return t, number, category, text

# ================= AI PARSER =================
def parse_with_ai(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "Extract finance data as JSON with keys: type, amount, category, note."
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        )

        data = json.loads(response.choices[0].message.content)

        return (
            data.get("type"),
            int(data.get("amount")),
            data.get("category"),
            data.get("note")
        )

    except Exception as e:
        print("AI FAILED:", e)
        return fallback_parse(text)

# ================= BOT =================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🤖 Finance bot ready! Send anything like: 'bought snacks 15k'")

@bot.message_handler(func=lambda message: True)
def handle(message):
    t, amount, category, note = parse_with_ai(message.text)

    try:
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            t,
            amount,
            category,
            note
        ])

        bot.reply_to(message, f"✅ Saved: {t} Rp{amount} ({category})")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ================= RUN =================
print("Bot running...")
bot.infinity_polling()

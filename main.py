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

# ================= NUMBER WORDS =================
words_to_numbers = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50
}

# ================= DATE =================
def extract_date(text):
    text_lower = text.lower()
    match = re.search(r"(\d{1,2} [a-zA-Z]+ \d{4})", text_lower)

    if match:
        date_str = match.group(1)
        for fmt in ["%d %B %Y", "%d %b %Y"]:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except:
                pass

    return datetime.now().strftime("%Y-%m-%d")

# ================= TIME =================
def extract_time(text):
    text_lower = text.lower()

    match = re.search(r"(\d{1,2}:\d{2})\s*(am|pm)", text_lower)

    if match:
        time_str = match.group(1)
        ampm = match.group(2)

        try:
            t = datetime.strptime(f"{time_str} {ampm}", "%I:%M %p")
            return t.strftime("%H:%M")
        except:
            pass

    return "00:00"

# ================= FALLBACK =================
def fallback_parse(text):
    text_lower = text.lower()

    # type
    if any(w in text_lower for w in ["bought", "spent", "paid"]):
        t = "Expense"
    elif any(w in text_lower for w in ["got", "earned", "received", "income"]):
        t = "Income"
    else:
        t = "Expense"

    # number
    number = 0
    match = re.search(r"\d+", text_lower)

    if match:
        number = int(match.group())
    else:
        for word, value in words_to_numbers.items():
            if word in text_lower:
                number = value
                break

    # multiplier (SAFE)
    if number < 1000:
        if "thousand" in text_lower or "k" in text_lower:
            number *= 1000
        elif "million" in text_lower or "jt" in text_lower:
            number *= 1000000

    # category
    if "food" in text_lower or "snack" in text_lower:
        category = "Food"
    elif "transport" in text_lower:
        category = "Transport"
    elif t == "Income":
        category = "Income"
    else:
        category = "Other"

    return t, number, category, text

# ================= AI =================
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

        t = data.get("type")
        amount = int(data.get("amount"))
        category = data.get("category")
        note = data.get("note")

        if amount <= 0:
            return fallback_parse(text)

        return t, amount, category, note

    except:
        return fallback_parse(text)

# ================= BOT =================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🤖 Finance bot ready!")

@bot.message_handler(func=lambda message: True)
def handle(message):
    t, amount, category, note = parse_with_ai(message.text)

    date = extract_date(message.text)
    time = extract_time(message.text)

    try:
        sheet.append_row([
            date,
            time,
            t,
            amount,
            category,
            note
        ])

        bot.reply_to(message, f"✅ Saved: {t} Rp{amount} on {date} {time}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ================= RUN =================
print("Bot running...")
bot.infinity_polling()

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

# ================= HELPERS =================
def get_all_data():
    return sheet.get_all_values()[1:]  # skip header

def calculate_balance():
    data = get_all_data()
    income = 0
    expense = 0

    for row in data:
        try:
            if row[2] == "Income":
                income += int(row[3])
            elif row[2] == "Expense":
                expense += int(row[3])
        except:
            pass

    return income, expense, income - expense

# ================= COMMANDS =================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🤖 Finance bot ready!")

@bot.message_handler(commands=['balance'])
def balance(message):
    income, expense, total = calculate_balance()
    bot.reply_to(message, f"💰 Balance: Rp{total}\n📈 Income: Rp{income}\n📉 Expense: Rp{expense}")

@bot.message_handler(commands=['today'])
def today(message):
    data = get_all_data()
    today_str = datetime.now().strftime("%Y-%m-%d")

    total = 0
    for row in data:
        try:
            if row[0] == today_str and row[2] == "Expense":
                total += int(row[3])
        except:
            pass

    bot.reply_to(message, f"📅 Today's spending: Rp{total}")

@bot.message_handler(commands=['summary'])
def summary(message):
    data = get_all_data()

    by_category = {}

    for row in data:
        try:
            if row[2] == "Expense":
                cat = row[4]
                amt = int(row[3])
                by_category[cat] = by_category.get(cat, 0) + amt
        except:
            pass

    text = "📊 Spending by category:\n"
    for cat, amt in by_category.items():
        text += f"- {cat}: Rp{amt}\n"

    bot.reply_to(message, text)

# ================= SIMPLE PARSER =================
def parse(text):
    text_lower = text.lower()

    # type
    if any(w in text_lower for w in ["bought", "spent", "paid"]):
        t = "Expense"
    elif any(w in text_lower for w in ["got", "earned", "received", "income"]):
        t = "Income"
    else:
        t = "Expense"

    # amount
    number = 0
    match = re.search(r"\d+", text_lower)
    if match:
        number = int(match.group())

        if number < 1000:
            if "thousand" in text_lower or "k" in text_lower:
                number *= 1000
            elif "million" in text_lower:
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

# ================= DATE + TIME =================
def extract_date(text):
    match = re.search(r"(\d{1,2} [a-zA-Z]+ \d{4})", text.lower())
    if match:
        try:
            return datetime.strptime(match.group(1), "%d %B %Y").strftime("%Y-%m-%d")
        except:
            pass
    return datetime.now().strftime("%Y-%m-%d")

def extract_time(text):
    match = re.search(r"(\d{1,2}:\d{2})\s*(am|pm)", text.lower())
    if match:
        t = datetime.strptime(f"{match.group(1)} {match.group(2)}", "%I:%M %p")
        return t.strftime("%H:%M")
    return "00:00"

# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda message: True)
def handle(message):
    t, amount, category, note = parse(message.text)
    date = extract_date(message.text)
    time = extract_time(message.text)

    try:
        sheet.append_row([date, time, t, amount, category, note])

        # smarter reply
        if t == "Expense":
            bot.reply_to(message, f"💸 Logged expense Rp{amount}. Careful bro 😏")
        else:
            bot.reply_to(message, f"💰 Nice! Income Rp{amount} added!")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ================= RUN =================
print("Bot running...")
bot.infinity_polling()

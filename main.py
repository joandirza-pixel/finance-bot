import os
import json
import re
from datetime import datetime
import matplotlib.pyplot as plt

import telebot
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI

# ================= SETUP =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client_sheets = gspread.authorize(creds)

sheet = client_sheets.open_by_key("1Jgrc4lmYveqNt5ydVT5xGhyAAyrQyY-yWls5xAEscoM").sheet1

# ================= DATA =================
def get_data():
    return sheet.get_all_values()[1:]

# ================= BALANCE =================
def calc():
    data = get_data()
    inc, exp = 0, 0

    for r in data:
        try:
            if r[2] == "Income":
                inc += int(r[3])
            elif r[2] == "Expense":
                exp += int(r[3])
        except:
            pass

    return inc, exp, inc - exp

# ================= PARSER =================
def parse(text):
    t = "Expense"
    if any(w in text.lower() for w in ["earned", "income", "got"]):
        t = "Income"

    num = 0
    m = re.search(r"\d+", text)
    if m:
        num = int(m.group())

        if num < 1000:
            if "k" in text.lower() or "thousand" in text.lower():
                num *= 1000
            if "million" in text.lower():
                num *= 1000000

    cat = "Other"
    if "food" in text.lower() or "snack" in text.lower():
        cat = "Food"

    return t, num, cat, text

# ================= DATE TIME =================
def extract_date(text):
    m = re.search(r"(\d{1,2} [a-zA-Z]+ \d{4})", text.lower())
    if m:
        try:
            return datetime.strptime(m.group(1), "%d %B %Y").strftime("%Y-%m-%d")
        except:
            pass
    return datetime.now().strftime("%Y-%m-%d")

def extract_time(text):
    m = re.search(r"(\d{1,2}:\d{2})\s*(am|pm)", text.lower())
    if m:
        t = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%I:%M %p")
        return t.strftime("%H:%M")
    return "00:00"

# ================= COMMANDS =================
@bot.message_handler(commands=['balance'])
def balance(msg):
    inc, exp, total = calc()
    bot.reply_to(msg, f"💰 Balance: Rp{total}\n📈 Income: Rp{inc}\n📉 Expense: Rp{exp}")

@bot.message_handler(commands=['chart'])
def chart(msg):
    data = get_data()

    cats = {}
    for r in data:
        try:
            if r[2] == "Expense":
                cats[r[4]] = cats.get(r[4], 0) + int(r[3])
        except:
            pass

    plt.figure()
    plt.pie(cats.values(), labels=cats.keys(), autopct='%1.1f%%')
    plt.savefig("chart.png")

    with open("chart.png", "rb") as f:
        bot.send_photo(msg.chat.id, f)

@bot.message_handler(commands=['monthly'])
def monthly(msg):
    data = get_data()
    now = datetime.now().strftime("%Y-%m")

    total = 0
    for r in data:
        if r[0].startswith(now) and r[2] == "Expense":
            total += int(r[3])

    bot.reply_to(msg, f"📅 This month spending: Rp{total}")

# ================= AI CHAT =================
@bot.message_handler(commands=['ask'])
def ask(msg):
    question = msg.text.replace("/ask", "")

    inc, exp, total = calc()

    prompt = f"""
User finance:
Income: {inc}
Expense: {exp}
Balance: {total}

User question: {question}
Answer like a smart finance assistant.
"""

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    bot.reply_to(msg, res.choices[0].message.content)

# ================= MAIN =================
@bot.message_handler(func=lambda m: True)
def handle(msg):
    t, amt, cat, note = parse(msg.text)
    date = extract_date(msg.text)
    time = extract_time(msg.text)

    sheet.append_row([date, time, t, amt, cat, note])

    # smart reply
    if t == "Expense" and amt > 50000:
        bot.reply_to(msg, f"💸 Rp{amt}?? bro you're spending a lot 😭")
    elif t == "Income":
        bot.reply_to(msg, f"💰 Nice! Rp{amt} added!")
    else:
        bot.reply_to(msg, f"✅ Logged Rp{amt}")

# ================= RUN =================
print("RUNNING...")
bot.infinity_polling()

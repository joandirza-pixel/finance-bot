@bot.message_handler(func=lambda message: True)
def handle(message):
    result = parse_with_ai(message.text)

    if not result:
        bot.reply_to(message, "❌ Couldn't understand")
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

        bot.reply_to(message, f"✅ Saved: {t} Rp{amount} ({category})")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

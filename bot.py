# ==================== Webhook ====================
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    try:
        # بنجبر الكود يقرأ الرابط الأساسي، وإذا ما لقاه بيعطيه الرابط الثابت
        base_url = os.getenv("RENDER_EXTERNAL_URL")
        if not base_url:
            base_url = "https://ichancy-bot-2.onrender.com"
        
        url = base_url + "/webhook"
        result = bot.set_webhook(url=url)
        return f"Webhook set to {url} | result={result}", 200
    except Exception as e:
        return f"Error: {str(e)}", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

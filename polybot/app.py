import flask
from flask import request
import os
import time
from collections import Counter
import telebot.apihelper
from polybot.bot import Bot, QuoteBot, ImageProcessingBot
from polybot.s3 import download_predicted_image_from_s3  # ✅ Make sure you import this!

app = flask.Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
BOT_APP_URL = os.environ['BOT_APP_URL']

# === Create bot instance early ===
bot = Bot(TELEGRAM_BOT_TOKEN, BOT_APP_URL)

@app.route('/', methods=['GET'])
def index():
    return 'Ok'

@app.route(f'/{TELEGRAM_BOT_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.route(req['message'])
    return 'Ok'

@app.route("/yolo_callback", methods=['POST'])
def yolo_callback():
    data = request.get_json()
    chat_id = data["chat_id"]
    labels = data["labels"]
    image_id = data["image_id"]

    # ✅ Always send text summary
    objects = Counter(labels)
    text = "✅ YOLO done! Objects found:\n"
    text += "\n".join([f"{obj} × {count}" for obj, count in objects.items()])
    bot.telegram_bot_client.send_message(chat_id, text)

    # ✅ Optional: Only send image if condition is met
    if int(image_id) % 2 == 0:
        tmp_predicted = f"/tmp/{chat_id}_{image_id}"
        download_predicted_image_from_s3(chat_id, image_id, tmp_predicted)
        with open(tmp_predicted, "rb") as img:
            bot.telegram_bot_client.send_photo(chat_id, img)
        os.remove(tmp_predicted)

    return {"status": "ok"}

if __name__ == "__main__":
    cert_path = "/home/ubuntu/TelegramBot/polybot.crt"

    try:
        webhook_info = bot.telegram_bot_client.get_webhook_info()
        if not webhook_info.url or webhook_info.url != f"{BOT_APP_URL}/{TELEGRAM_BOT_TOKEN}/":
            bot.telegram_bot_client.set_webhook(
                url=f"{BOT_APP_URL}/{TELEGRAM_BOT_TOKEN}/",
                certificate=open(cert_path, "rb")
            )
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Failed to set webhook: {e}")

    app.run(host='0.0.0.0', port=8443)

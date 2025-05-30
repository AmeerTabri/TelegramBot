import flask
from flask import request
import os
from polybot.bot import Bot, QuoteBot, ImageProcessingBot


app = flask.Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
BOT_APP_URL = os.environ['BOT_APP_URL']


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_BOT_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


# if __name__ == "__main__":
#     cert_path = "/home/ubuntu/TelegramBot/polybot.crt"
#     bot = ImageProcessingBot(TELEGRAM_BOT_TOKEN, BOT_APP_URL)
#
#     # Set webhook with certificate
#     bot.telegram_bot_client.set_webhook(
#         url=f"{BOT_APP_URL}/{TELEGRAM_BOT_TOKEN}/",
#         certificate=open(cert_path, "r")
#     )
#
#     app.run(host='0.0.0.0', port=8443)
#

if __name__ == "__main__":
    import telebot.apihelper
    import time

    cert_path = "/home/ubuntu/TelegramBot/polybot.crt"
    bot = ImageProcessingBot(TELEGRAM_BOT_TOKEN, BOT_APP_URL)

    try:
        # Only set webhook if it's not already set
        webhook_info = bot.telegram_bot_client.get_webhook_info()
        if not webhook_info.url or webhook_info.url != f"{BOT_APP_URL}/{TELEGRAM_BOT_TOKEN}/":
            bot.telegram_bot_client.set_webhook(
                url=f"{BOT_APP_URL}/{TELEGRAM_BOT_TOKEN}/",
                certificate=open(cert_path, "r")
            )
    except telebot.apihelper.ApiTelegramException as e:
        print(f"Failed to set webhook: {e}")
        # Optional: wait and retry or continue without setting it again

    app.run(host='0.0.0.0', port=8443)

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


if __name__ == "__main__":
    bot = ImageProcessingBot(
        "7663738647:AAHiDJ75yGt89pFzVWkNp1kLCHwViM9egAo",
        "https://52.36.176.111"
    )

    # Set webhook with certificate
    bot.telegram_bot_client.set_webhook(
        url="https://52.36.176.111/7663738647:AAHiDJ75yGt89pFzVWkNp1kLCHwViM9egAo/",
        certificate=open("/home/ubuntu/TelegramBot/polybot.crt", "r")
    )

    app.run(host='0.0.0.0', port=8443)


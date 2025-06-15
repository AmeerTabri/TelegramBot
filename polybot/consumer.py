import os
import json
import time
import boto3
from loguru import logger
from telebot import TeleBot
from telebot.types import InputFile
from pathlib import Path
from polybot.s3 import download_predicted_image_from_s3

# === Config ===
AWS_REGION = os.environ.get('AWS_REGION', 'us-west-2')
QUEUE_URL = 'https://sqs.us-west-2.amazonaws.com/228281126655/ameer-polybot-chat-messages'
TELEGRAM_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']

sqs = boto3.client('sqs', region_name=AWS_REGION)
bot = TeleBot(TELEGRAM_TOKEN)


def handle_message(msg_body: dict):
    chat_id = msg_body['chat_id']
    s3_key = msg_body['image_s3_key']

    logger.info(f"Processing message for chat_id: {chat_id}")

    # === 1) Download only the predicted image ===
    Path("temp").mkdir(exist_ok=True)
    predicted_path = f"temp/{chat_id}_predicted.jpg"
    image_name = Path(s3_key).name

    download_predicted_image_from_s3(chat_id, image_name, predicted_path)

    # === 2) Send predicted image to user ===
    bot.send_photo(chat_id, InputFile(predicted_path))
    bot.send_message(chat_id, "✅ Your prediction is ready!")

    # === 3) Cleanup ===
    os.remove(predicted_path)
    logger.info(f"Finished processing message for chat_id: {chat_id}")


while True:
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=5,
        WaitTimeSeconds=20
    )

    messages = response.get('Messages', [])

    for msg in messages:
        msg_body = json.loads(msg['Body'])
        handle_message(msg_body)

        # Delete message after successful processing
        sqs.delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=msg['ReceiptHandle']
        )
        logger.info(f"Message deleted: {msg['MessageId']}")

    if not messages:
        time.sleep(1)

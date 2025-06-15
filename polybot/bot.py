import os
import time
import shutil
from pathlib import Path
from collections import Counter
import telebot
from loguru import logger
from telebot.types import InputFile
from polybot.img_proc import Img
from polybot.s3 import upload_image_to_s3, download_predicted_image_from_s3


class Bot:
    def __init__(self, token, telegram_chat_url):
        self.telegram_bot_client = telebot.TeleBot(token)
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)
        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

        self.processor = ImageProcessingBot(self.telegram_bot_client)
        self.predictor = ImagePredictionBot(self.telegram_bot_client)

    def route(self, msg):
        chat_id = msg['chat']['id']
        if not self.is_current_msg_photo(msg):
            text = msg.get('text', '').strip().lower()
            if text == '/start':
                self.send_greeting(chat_id)
            elif text == 'captions':
                self.processor.send_filter_list(chat_id)
            elif text == 'ai':
                self.predictor.send_ai_list(chat_id)
            else:
                self.send_text(chat_id, "Please send me an image.")
            return

        caption = msg.get('caption', '').strip().lower()
        if caption.startswith('predict'):
            self.predictor.handle_image(msg, caption)
        else:
            self.processor.handle_image(msg)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_greeting(self, chat_id):
        greeting = (
            "👋 Hi there! Welcome to PolyBot.\n"
            "Send a *photo* with a *caption*.\n"
            "- Type *captions* for image filters\n"
            "- Type *AI* for AI features\n"
            "- Use commas to apply multiple filters"
        )
        self.telegram_bot_client.send_message(chat_id, greeting, parse_mode='Markdown')
        self.processor.send_filter_list(chat_id)
        self.predictor.send_ai_list(chat_id)


class QuoteBot(Bot):
    def handle_quote(self, msg):
        chat_id = msg['chat']['id']
        text = msg.get("text", "")
        if text != "Please don't quote me":
            self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=msg["message_id"])


class ImageProcessingBot:
    def __init__(self, bot_client):
        self.bot = bot_client

    def send_filter_list(self, chat_id):
        filters = (
            "The Available Filters Are:\n"
            "1) *blur* - Smoothens the image.\n"
            "2) *contour* - Detects edges.\n"
            "3) *rotate* - Rotates the image 90° clockwise.\n"
            "4) *segment* - Segments light/dark regions.\n"
            "5) *salt and pepper* - Adds random noise.\n"
            "6) *concat* - Concatenates the image with itself.\n"
            "7) *invert* - Inverts pixel intensities.\n"
            "8) *binary* - Converts to black & white.\n"
            "9) *flip* - Flips the image.\n"
            "10) *pixel* - Pixelates the image.\n"
            "Note1: *concat* and *flip* can be applied in *horizontal* or *vertical* direction.\n"
            "Note2: *blur* and *pixel* can be given a level value.\n"
            "Note3: Use *concat1* to upload the first image and *concat2* to upload the second image for concatenation.\n"
        )
        self.bot.send_message(chat_id, filters, parse_mode='Markdown')

    def handle_image(self, msg):
        chat_id = msg['chat']['id']
        try:
            file_info = self.bot.get_file(msg['photo'][-1]['file_id'])
            data = self.bot.download_file(file_info.file_path)
            folder = file_info.file_path.split('/')[0]
            os.makedirs(folder, exist_ok=True)
            with open(file_info.file_path, 'wb') as f:
                f.write(data)
            img_path = file_info.file_path
            img = Img(img_path)

            caption_raw = msg.get('caption', '').strip().lower()
            captions = [c.strip() for c in caption_raw.split(',') if c.strip()]
            if not captions:
                self.bot.send_message(chat_id, "Please provide at least one filter in the caption.")
                return

            for caption in captions:
                try:
                    if caption == 'concat1':
                        user_dir = Path(f'temp/{chat_id}')
                        user_dir.mkdir(parents=True, exist_ok=True)
                        saved_path = img.save_img()
                        shutil.copy(saved_path, user_dir / 'first_img.jpg')
                        self.bot.send_message(chat_id, "Send the second image with the direction.")
                        os.remove(saved_path)
                        os.remove(img_path)
                        return

                    if caption.startswith('concat2'):
                        parts = caption.split()
                        direction = parts[1] if len(parts) > 1 else 'horizontal'
                        first_img_path = Path(f'temp/{chat_id}/first_img.jpg')
                        if not first_img_path.exists():
                            self.bot.send_message(chat_id, "First image not found.")
                            return
                        first_img = Img(str(first_img_path))
                        img.concat(first_img, direction)
                        first_img_path.unlink(missing_ok=True)
                        continue

                    if caption.startswith('blur'):
                        parts = caption.split()
                        level = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 16
                        img.blur(level)
                    elif caption == 'contour':
                        img.contour()
                    elif caption == 'rotate':
                        img.rotate()
                    elif caption == 'segment':
                        img.segment()
                    elif caption == 'salt and pepper':
                        img.salt_n_pepper()
                    elif caption.startswith('concat'):
                        parts = caption.split()
                        direction = parts[1] if len(parts) > 1 and parts[1] in ['horizontal', 'vertical'] else 'horizontal'
                        img.concat(img, direction)
                    elif caption.startswith('flip'):
                        parts = caption.split()
                        direction = parts[1] if len(parts) > 1 else 'vertical'
                        img.flip(direction)
                    elif caption == 'invert':
                        img.invert()
                    elif caption == 'binary':
                        img.binary()
                    elif caption.startswith('pixel'):
                        parts = caption.split()
                        level = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
                        img.pixelate(level)
                    elif caption.startswith('predict'):
                        show_image = 'show' in caption
                        predictions = img.predict(chat_id)
                        self.bot.send_message(chat_id, f"Predictions = {predictions}")

                        s3_key = f"{chat_id}/original/{Path(img_path).name}"
                        upload_image_to_s3(img_path, s3_key)

                        if show_image:
                            predicted_path = f"temp/{chat_id}_predicted{Path(img_path).suffix}"
                            try:
                                download_predicted_image_from_s3(chat_id, Path(img_path).name, predicted_path)
                                self.bot.send_photo(chat_id, InputFile(predicted_path))
                                os.remove(predicted_path)
                            except Exception as e:
                                logger.warning(f"Could not fetch predicted image from S3: {e}")

                        return
                    else:
                        self.bot.send_message(chat_id, f"Invalid filter: {caption}")
                        return
                except RuntimeError as e:
                    self.bot.send_message(chat_id, f"Error: {str(e)}")
                    return

            processed_path = img.save_img()
            self.bot.send_photo(chat_id, InputFile(processed_path))
            os.remove(processed_path)
            os.remove(img_path)

        except Exception as e:
            logger.error(f"ImageProcessingBot error: {e}")
            self.bot.send_message(chat_id, "Error processing image.")


class ImagePredictionBot:
    def __init__(self, bot_client):
        self.bot = bot_client

        import boto3
        self.sqs = boto3.client(
            'sqs',
            region_name=os.environ.get('AWS_REGION', 'us-west-2')
        )
        self.QUEUE_URL = 'https://sqs.us-west-2.amazonaws.com/228281126655/ameer-polybot-chat-messages'

    def send_ai_list(self, chat_id):
        text = (
            "AI Features:\n"
            "*predict* – Detects objects in the image\n"
            "*predict show* – Detects objects and returns the annotated image"
        )
        self.bot.send_message(chat_id, text, parse_mode='Markdown')

    def handle_image(self, msg, caption='predict'):
        chat_id = msg['chat']['id']
        show_image = 'show' in caption
        os.makedirs("temp", exist_ok=True)

        try:
            # 1) Download image from Telegram
            file_info = self.bot.get_file(msg['photo'][-1]['file_id'])
            data = self.bot.download_file(file_info.file_path)
            ext = Path(file_info.file_path).suffix or '.jpg'
            tmp_original_path = f"temp/{chat_id}_original{ext}"

            with open(tmp_original_path, 'wb') as f:
                f.write(data)

            # 2) Upload to S3
            s3_key = f"{chat_id}/original/{Path(tmp_original_path).name}"
            upload_image_to_s3(tmp_original_path, s3_key)

            # 3) Push job to SQS for YOLO to process
            self._send_to_queue(chat_id, s3_key, show_image)

            self.bot.send_message(chat_id, "✅ Your image was sent for prediction. You will get the result soon.")

            os.remove(tmp_original_path)

        except Exception as e:
            logger.error(f"ImagePredictionBot error: {e}")
            self.bot.send_message(chat_id, "⚠️ Failed to process your image. Please try again later.")

    def _send_to_queue(self, chat_id, s3_key, show_image):
        import json
        try:
            response = self.sqs.send_message(
                QueueUrl=self.QUEUE_URL,
                MessageBody=json.dumps({
                    "chat_id": chat_id,
                    "image_s3_key": s3_key,
                    "show_image": show_image
                })
            )
            logger.info(f"SQS: Job sent for YOLO. ID: {response['MessageId']}")
        except Exception as e:
            logger.error(f"SQS: Failed to send message: {e}")
            self.bot.send_message(chat_id, "⚠️ Failed to queue your request.")

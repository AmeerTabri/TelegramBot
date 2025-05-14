import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from polybot.img_proc import Img
import shutil
from pathlib import Path
from polybot.s3 import upload_image_to_s3, download_predicted_image_from_s3


def is_current_msg_photo(msg):
    return 'photo' in msg


class Bot:
    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def download_user_photo(self, msg):
        if not is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')

    def send_greeting(self, chat_id):
        greeting = (
            "👋 Hi there! Welcome to PolyBot.\n"
            "You can send me a *photo* with a *caption* specifying one or more filters (comma-separated).\n"
            "You can also send me a *photo* with predict caption to list the objects"
            "For a list of available filters, type: *captions*"
        )
        self.telegram_bot_client.send_message(chat_id, greeting, parse_mode='Markdown')


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ImageProcessingBot(Bot):
    def send_filter_list(self, chat_id):
        filter_list = (
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
            "Note3: Use *concat1* to upload the first image and *concat1* to upload the second image for concatenation.\n"
        )
        self.telegram_bot_client.send_message(chat_id, filter_list, parse_mode='Markdown')

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        chat_id = msg['chat']['id']

        try:
            if not is_current_msg_photo(msg):
                text = msg['text'].strip().lower()
                if text == '/start':
                    self.send_greeting(chat_id)
                elif text == 'captions':
                    self.send_filter_list(chat_id)
                else:
                    self.send_text(chat_id, "Please send me an image")
                return

            img_path = self.download_user_photo(msg)
            logger.info(f"Downloaded photo to: {img_path}")

            img = Img(img_path)

            caption_raw = msg.get('caption', '').strip().lower()
            captions = [cap.strip() for cap in caption_raw.split(',') if cap.strip()]

            if not captions:
                self.send_text(chat_id, "Please provide at least one filter in the caption.")
                return

            for caption in captions:
                try:
                    if caption == 'concat1':
                        user_dir = Path(f'temp/{chat_id}')
                        user_dir.mkdir(parents=True, exist_ok=True)
                        saved_path = img.save_img()
                        first_img_path = user_dir / 'first_img.jpg'
                        shutil.copy(saved_path, first_img_path)
                        self.send_text(chat_id, "Send the second image with direction.")
                        return

                    elif caption.startswith('concat2'):
                        parts = caption.split()
                        direction = parts[1] if len(parts) > 1 and parts[1] in ['horizontal', 'vertical'] else 'horizontal'
                        first_img_path = Path(f'temp/{chat_id}/first_img.jpg')
                        if not first_img_path.exists():
                            self.send_text(chat_id, "First image not found. Please send the first image.")
                            return

                        first_img = Img(str(first_img_path))
                        img.concat(first_img, direction)
                        first_img_path.unlink()
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
                        direction = parts[1] if len(parts) > 1 and parts[1] in ['horizontal', 'vertical'] else 'vertical'
                        img.flip(direction)
                    elif caption == 'invert':
                        img.invert()
                    elif caption == 'binary':
                        img.binary()
                    elif caption.startswith('pixel'):
                        parts = caption.split()
                        level = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10
                        img.pixelate(level)
                    elif caption == 'predict':
                        s3_key = f"{chat_id}/original/{Path(img_path).name}"
                        upload_image_to_s3(img_path, s3_key)

                        predictions = img.predict(chat_id)
                        if not predictions:
                            self.send_text(chat_id, "⚠️ Yolo service is not responding. Please try again later!")
                            return

                        self.send_text(chat_id, f"Predictions = {predictions}")

                        image_name = Path(img_path).name
                        predicted_path = f"/tmp/predicted_{image_name}"
                        download_predicted_image_from_s3(chat_id, image_name, predicted_path)
                        self.send_photo(chat_id, predicted_path)
                        return
                    else:
                        self.send_text(chat_id, f"Invalid filter: {caption}\nFor the filters list type: captions")
                        return
                except RuntimeError as e:
                    self.send_text(chat_id, f"Error: {str(e)}")
                    return

            img.save_img()
            processed_path = img.save_img()
            logger.info(f"Processed image saved at: {processed_path}")
            self.send_photo(chat_id, processed_path)

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            self.send_text(chat_id, "Something went wrong... please try again.")


class ImagePredictionBot(Bot):
    def send_ai_list(self, chat_id):
        yolo_list = (
            "The Available AI features Are:\n"
            "*predict*: list the objects of the picture"
        )
        self.telegram_bot_client.send_message(chat_id, yolo_list, parse_mode='Markdown')

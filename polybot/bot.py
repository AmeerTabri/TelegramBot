import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from img_proc import Img


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

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
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


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ImageProcessingBot(Bot):
    def send_greeting(self, chat_id):
        greeting = (
            "👋 Hi there! Welcome to PolyBot.\n"
            "Send me a *photo* with a *caption* specifying one or more filters (comma-separated).\n"
            "For a list of available filters, type: *captions*"
        )
        self.telegram_bot_client.send_message(chat_id, greeting, parse_mode='Markdown')
        self.send_filter_list(chat_id)

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
            "9) *flip* - Flips the image horizontally.\n"
            "Note: *concat* and *flip* can be applied in *horizontal* or *vertical* direction.\n"
        )
        self.telegram_bot_client.send_message(chat_id, filter_list, parse_mode='Markdown')

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        chat_id = msg['chat']['id']

        try:
            if not self.is_current_msg_photo(msg):
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
                    if caption == 'blur':
                        img.blur()
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
                        direction = parts[1] if len(parts) > 1 and parts[1] in ['horizontal',
                                                                                'vertical'] else 'horizontal'
                        other_img = Img(img_path)
                        img.concat(other_img, direction)
                    elif caption.startswith('flip'):
                        parts = caption.split()
                        direction = parts[1] if len(parts) > 1 and parts[1] in ['horizontal',
                                                                                'vertical'] else 'vertical'
                        img.flip(direction)
                    elif caption == 'invert':
                        img.invert()
                    elif caption == 'binary':
                        img.binary()
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

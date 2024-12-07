from telegram import Bot
import logging
from src import (
    chat_id,
    bot_token
)

def upload_file_to_telegram(file_path):
    try:
        bot = Bot(token=bot_token)
        with open(file_path, 'rb') as file:
            bot.send_document(chat_id=chat_id, document=file)

        logging.info("Upload to Telegram Chanel success!")
    except Exception as e:
        logging.error(f"Error when upload to Telegram: {e}")

from telegram import Bot
import logging
from src import (
    chat_id,
    bot_token
)

async def upload_file_to_telegram(file_path):
    try:
        bot = Bot(token=bot_token)
        with open(file_path, 'rb') as file:
            await bot.send_document(chat_id=chat_id, document=file)

        logging.info("Upload to Telegram Channel success!")
    except Exception as e:
        logging.error(f"Error when uploading to Telegram: {e}")

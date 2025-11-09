import atexit
import re
from asyncio import new_event_loop, set_event_loop
from datetime import datetime
from sys import maxsize
from typing import List
from telethon import TelegramClient
from telethon.tl.custom import Message
from config_handler import tg_messages_signs
from configs.config import MessageTypes


def init_tg_client(api_id, api_hash, phone, password=None) -> TelegramClient:
    """
    Инициализирует клиент Telegram
    """
    global _tg_client
    _tg_client = TelegramClient('.session', api_id, api_hash).start(phone, password)
    return _tg_client


def get_new_messages(tg_client: TelegramClient, bot_name: str, last_date: datetime) -> List[Message]:
    # Получаем ID бота
    bot = loop.run_until_complete(tg_client.get_entity(bot_name))
    # Устанавливаем параметры фильтрации по минимальной дате через id сообщений
    message_from = loop.run_until_complete(
        tg_client.get_messages(entity=bot.id, offset_date=last_date, limit=1))
    # Формируем параметры фильтра для получения сообщений
    message_filters = dict(entity=bot.id, reverse=True, wait_time=0.1)
    message_filters['min_id'] = message_from[0].id if message_from else 0
    message_filters['max_id'] = maxsize
    # Получаем новые сообщения из чата
    message_list = loop.run_until_complete(tg_client.get_messages(**message_filters))
    return message_list


def tg_detect_message_type(message_text: str) -> MessageTypes:
    """
    Определяет тип сообщения Telegram по его тексту
    """
    result = MessageTypes.TG_UNKNOWN
    for config_type_name in tg_messages_signs.model_fields.keys():
        matching = re.search(f"{'|'.join(getattr(tg_messages_signs, config_type_name))}", message_text)
        if matching:
            result = MessageTypes.get_message_type_by_config_name(config_type_name)
    return result


def cleanup_loop():
    """
    Вызывается при завершении приложения и закрывает цикл событий, если он открыт.
    """
    if loop.is_running():
        loop.stop()
    if not loop.is_closed():
        loop.close()
    set_event_loop(None)


# Создаем и сохраняем цикл событий
loop = new_event_loop()
set_event_loop(loop)
atexit.register(cleanup_loop)
# Creating a client for working with Telegram / Создание клиента для работы с Telegram
_tg_client = None

if __name__ == '__main__':
    pass

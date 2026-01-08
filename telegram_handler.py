from asyncio import new_event_loop, set_event_loop, all_tasks, gather
from datetime import datetime
from sys import maxsize
from typing import List
from telethon import TelegramClient
from telethon.tl.custom import Message


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
    # Формируем параметры фильтра для получения сообщений
    message_filters = dict(entity=bot.id, reverse=True, wait_time=0.1)
    # Устанавливаем параметры фильтрации по минимальной дате через id сообщений
    message_filters['min_id'] = 0
    message_filters['max_id'] = maxsize
    if last_date is not None:
        message_from = loop.run_until_complete(tg_client.get_messages(entity=bot.id, offset_date=last_date, limit=1))
        message_filters['min_id'] = message_from[0].id if message_from else 0
    # Получаем новые сообщения из чата
    message_list = loop.run_until_complete(tg_client.get_messages(**message_filters))
    return message_list


async def disconnect_client(tg_client: TelegramClient):
    """
    Асинхронное отключение клиента
    """
    if tg_client.is_connected():
        await tg_client.disconnect()


def cleanup_loop(tg_client: TelegramClient):
    """
    Вызывается при завершении приложения. Отключает клиент и закрывает цикл событий, если он открыт.
    """
    try:
        # Отключаем клиент
        if not loop.is_closed():
            loop.run_until_complete(disconnect_client(tg_client))
        # Отменяем pending задачи
        if not loop.is_closed():
            pending = all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(gather(*pending, return_exceptions=True))
        # Закрываем loop
        if not loop.is_closed():
            loop.close()
    except Exception as e:
        print(f"Telegram client and loop cleanup error: {e}")


# Создаем и сохраняем цикл событий
loop = new_event_loop()
set_event_loop(loop)
# Creating a client for working with Telegram / Создание клиента для работы с Telegram
_tg_client = None

if __name__ == '__main__':
    pass

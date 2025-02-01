import re
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.tl.types import MessageEntityTextUrl

from database_handler import *


async def main():
    bot = await client.get_entity(settings['BOT_NAME'])
    messages_list = await client.get_messages(bot.id, add_offset=10, limit=10, wait_time=0.1)
    for message in messages_list:
        source_message = SourceMessage(message_id=message.id, date=message.date,
                                       message_type='', text=message.text, urls='')
        session.add(source_message)
    session.commit()
    # print(message.text)
    # for entity in message.entities:
    #     print(type(entity))
    #     print(entity.to_dict())
    #     if isinstance(entity, MessageEntityTextUrl):
    #         print(entity.url)
    #     print('------------------')


# def retrieve_url_from_message(message):
#     for entity in message.entities:
#         if isinstance(entity, MessageEntityTextUrl):
#             return entity.url
#     return None
#
# def retrieve_url_from_message_text(text):
#     url_pattern = r"https?://\S+"
#     return re.findall(url_pattern, text)


def load_env(file_path=".env") -> dict:
    """ Загружает конфиденциальные данные из файла .env """
    env_vars = {}
    with open(file_path, 'r') as file_env:
        for line in file_env:
            if not line.strip().startswith('#') and '=' in line:
                key, value = line.strip().split('=')
                env_vars[key] = value
    return env_vars


if __name__ == '__main__':
    # Загрузка параметров Telegram API
    settings = load_env()
    # Подключение к базе данных
    session = connect_database()
    # Создание клиента для работы с Telegram
    client = (TelegramClient(session=MemorySession(), api_id=settings['APP_API_ID'],
                             api_hash=settings['APP_API_HASH']).start(settings['PHONE'], settings['PASSWORD']))
    with client:
        client.loop.run_until_complete(main())

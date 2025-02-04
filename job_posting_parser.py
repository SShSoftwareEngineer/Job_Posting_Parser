import re
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.tl.types import MessageEntityTextUrl

from database_handler import *


def load_env(file_path) -> dict:
    """ Загружает конфиденциальные данные из файла .env """
    env_vars = {}
    with open(file_path, 'r', encoding='utf-8') as file_env:
        for line in file_env:
            if not line.strip().startswith('#') and '=' in line:
                key, value = line.strip().split('=')
                env_vars[key] = value
    return env_vars



# def retrieve_url_from_message(message):
#     for entity in message.entities:
#         if isinstance(entity, MessageEntityTextUrl):
#             return entity.url
#     return None
#
# def retrieve_url_from_message_text(text):
#     url_pattern = r"https?://\S+"
#     return re.findall(url_pattern, text)


async def main():
    # Определяем ID последнего сообщения в базе данных
    last_message_id = 0
    if session.query(SourceMessage).count():
        last_message_id = max(map(lambda x: x[0], (session.query(SourceMessage.message_id))))
    # Получаем новые сообщения
    bot = await client.get_entity(private_settings['BOT_NAME'])
    messages_list = client.iter_messages(bot.id, reverse=True, min_id=last_message_id,
                                         wait_time=0.1, limit=100)  # , limit=10
    # Определяем тип сообщений и сохраняем их в базу данных
    async for message in messages_list:
        source_message = SourceMessage(message_id=message.id,
                                       date=message.date,
                                       text=message.text)
        print(source_message.message_type)
        session.add(source_message)
    session.commit()


if __name__ == '__main__':
    # Загрузка конфиденциальных параметров Telegram API
    private_settings = load_env('.env')
    # Загрузка шаблонов базы данных из файла
    read_db_data()
    # Подключение к базе данных
    session = connect_database()
    # Создание клиента для работы с Telegram
    client = (TelegramClient(session='.session',  # MemorySession(),
                             api_id=private_settings['APP_API_ID'],
                             api_hash=private_settings['APP_API_HASH']).start(private_settings['PHONE'],
                                                                              private_settings['PASSWORD']))
    with client:
        client.loop.run_until_complete(main())

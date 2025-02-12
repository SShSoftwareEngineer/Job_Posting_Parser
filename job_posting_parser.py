import aiohttp
from telethon import TelegramClient
# from telethon.sessions import MemorySession

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


async def main():
    # Определяем ID последнего сообщения в базе данных
    last_message_id = 0
    if session.query(SourceMessage).count():
        last_message_id = max(map(lambda x: x[0], (session.query(SourceMessage.message_id))))

    last_message_id = max(10000, last_message_id)

    # Получаем новые сообщения из чата
    bot = await client.get_entity(private_settings['BOT_NAME'])
    messages_list = client.iter_messages(bot.id, reverse=True, min_id=last_message_id,
                                         wait_time=0.1, limit=50)  # , limit=10
    # Создаем сессию для работы с HTTP-запросами
    timeout = aiohttp.ClientTimeout(total=20)  # Устанавливаем тайм-аут запроса
    async with aiohttp.ClientSession(timeout=timeout) as http_session:
        # Обрабатываем полученный список сообщений
        async for message in messages_list:
            # Определяем тип исходных сообщений
            source_message = SourceMessage(message_id=message.id, date=message.date, text=message.text)
            detail_messages = list()
            # Создаем детальные сообщения в зависимости от типа исходного сообщения
            match source_message.message_type:
                case 'vacancy':
                    # Разбиваем сообщение на отдельные вакансии
                    vacancies = re.split(get_vacancy_pattern(), source_message.text)
                    # Обрабатываем вакансии
                    for vacancy in vacancies:
                        if vacancy.strip('\n'):
                            # Извлекаем URL вакансии
                            vacancy_url = re.search(f'{get_vacancy_url_pattern()}', vacancy).group(0)
                            # Получаем HTML-код страницы вакансии
                            try:
                                async with http_session.get(vacancy_url) as response:
                                    match response.status:
                                        case 200:
                                            vacancy_html = await response.text()
                                        case 404:
                                            vacancy_html = '404 Not Found'
                                        case _:
                                            vacancy_html = f'Error {response.status}'
                            except aiohttp.ClientError as e:
                                vacancy_html = f'Error {e}'
                            # Сохраняем сообщение о вакансии в список
                            detail_messages.append(
                                VacancyMessage(source_message=source_message, text=vacancy.strip(' \n'),
                                               raw_html=vacancy_html.strip(' \n')))
                case 'statistic':
                    # Создаем сообщение со статистикой
                    detail_messages.append(StatisticMessage(source_message=source_message))
                case 'service':
                    # Создаем сервисное сообщение
                    detail_messages.append(ServiceMessage(source_message=source_message))
            # Записываем исходное и детальные сообщения в сессию
            session.add(source_message)
            for detail_message in detail_messages:
                session.add(detail_message)
            # Сохраняем сообщения в базе данных
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

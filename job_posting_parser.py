import aiohttp
from telethon import TelegramClient
from tqdm.asyncio import tqdm
from collections import Counter

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
    # Получаем новые сообщения из чата
    bot = await client.get_entity(private_settings['BOT_NAME'])
    messages_list = client.iter_messages(bot.id, reverse=True, min_id=last_message_id,
                                         wait_time=0.1, limit=200)  # , limit=10
    print(f'   New messages: {messages_list.left}')
    # Создаем HTTP сессию для работы с HTTP-запросами.
    # Задаем тайм-аут запроса
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as http_session:
        # Обрабатываем полученный список сообщений
        async for message in tqdm(messages_list, total=messages_list.left, desc='Processing ', ncols=50):
            # Определяем тип исходных сообщений
            source = SourceMessage(message_id=message.id, date=message.date, text=message.text)
            if source.message_type is None:
                message_types['unknown'] += 1
            details = list()
            # Создаем детальные сообщения в зависимости от типа исходного сообщения
            match source.message_type:
                case 'vacancy':
                    # Разбиваем сообщение на отдельные вакансии
                    vacancies = re.split(config.get_vacancy_pattern(), source.text)
                    # Обрабатываем вакансии
                    for vacancy in vacancies:
                        if vacancy.strip('\n'):
                            # Извлекаем URL вакансии
                            vacancy_url = re.search(config.get_url_pattern(), vacancy)[0]
                            # Получаем HTML-код страницы вакансии
                            try:
                                async with http_session.get(vacancy_url) as response:
                                    match response.status:
                                        case 200:
                                            vacancy_html = await response.text()
                                        case 404:
                                            vacancy_html = 'Error 404 Not Found'
                                        case _:
                                            vacancy_html = f'Error {response.status}'
                            except aiohttp.ClientError as e:
                                vacancy_html = f'Error {e}'
                            # Дописываем сообщение об ошибке доступа, если IP был заблокирован
                            if re.search(r'Your IP address.*?has been blocked', vacancy_html):
                                vacancy_html = f'Error 403 Forbidden or 429 Too Many Requests. {vacancy_html}'
                            # Сохраняем сообщение о вакансии в список
                            details.append(
                                VacancyMessage(source=source, text=vacancy.strip(' \n'),
                                               raw_html=vacancy_html.strip(' \n')))
                    message_types['vacancy'] += 1
                case 'statistic':
                    # Создаем сообщение со статистикой
                    details.append(StatisticMessage(source=source))
                    message_types['statistic'] += 1
                case 'service':
                    # Создаем сервисное сообщение
                    details.append(ServiceMessage(source=source))
                    message_types['service'] += 1
            # Записываем исходное и детальные сообщения в сессию
            session.add(source)
            session.add_all(details)
            # Сохраняем сообщения в базе данных
            session.commit()


if __name__ == '__main__':
    # Загрузка конфиденциальных параметров Telegram API
    private_settings = load_env('.env')
    # Инициализация счетчика сообщений
    message_types = Counter()
    # Создание клиента для работы с Telegram
    client = (TelegramClient(session='.session',  # MemorySession(),
                             api_id=private_settings['APP_API_ID'],
                             api_hash=private_settings['APP_API_HASH']).start(private_settings['PHONE'],
                                                                              private_settings['PASSWORD']))
    with client:
        client.loop.run_until_complete(main())

    export_data_to_excel()
    print('   Report:')
    print(f'Vacancy:   {message_types.get('vacancy', 0)}')
    print(f'Statistic: {message_types.get('statistic', 0)}')
    print(f'Service:   {message_types.get('service', 0)}')
    print(f'Unknown:   {message_types.get('unknown', 0)}')

# TODO: Unit тесты
# TODO: Проверить еще качество парсинга HTML
# TODO: Все откомментировать
# TODO: Расписать проект в README

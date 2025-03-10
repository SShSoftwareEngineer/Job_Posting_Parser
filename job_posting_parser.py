""" Скрипт реализует основную логику проекта

Инициализируются переменные:
private_settings - словарь с конфиденциальными данными для работы с Telegram API
message_types_counter - счетчик сообщений всех типов
client - объект клиента Telegram
Функции:
load_env(file_path) - функция для чтения конфиденциальных данных из файла .env для работы с Telegram API
async def main(client_telegram, priv_settings, message_types) - асинхронная функция для получения и
обработки сообщений из чата Telegram
"""

from collections import Counter, namedtuple
import re
import aiohttp
from telethon import TelegramClient # type: ignore
from tqdm.asyncio import tqdm
from database_handler import SourceMessage, VacancyMessage, StatisticMessage, ServiceMessage, \
    HTTP_ERRORS, session, config, export_data_to_excel


def load_env(file_path: str) -> dict:
    """ Загружает конфиденциальные данные из файла .env

    Arguments:
    file_path (str): имя файла с конфиденциальными данными
    Returns:
    dict - словарь с конфиденциальными данными
    """
    env_vars = {}
    with open(file_path, 'r', encoding='utf-8') as file_env:
        for line in file_env:
            if not line.strip().startswith('#') and '=' in line:
                key, value = line.strip().split('=')
                env_vars[key] = value
    return env_vars


# Кортеж, соответствующий структуре данных вакансии
Vacancy = namedtuple('Vacancy', ['text', 'url', 'html'])


async def main(client_telegram, priv_settings, message_types):
    """ Получает и обрабатывает сообщения из чата Telegram

    Arguments:
    client_telegram - объект клиента Telegram
    priv_settings - словарь с конфиденциальными данными для работы с Telegram API
    message_types - счетчик сообщений всех типов
    """
    # Определяем ID последнего сообщения в базе данных
    last_message_id = 0
    if session.query(SourceMessage).count():
        last_message_id = max(map(lambda x: x[0], (session.query(SourceMessage.message_id))))
    # Получаем новые сообщения из чата
    bot = await client_telegram.get_entity(priv_settings['BOT_NAME'])
    messages_list = client_telegram.iter_messages(bot.id, reverse=True, min_id=last_message_id, wait_time=0.1)
    print(f'   New messages: {messages_list.left}')
    # Создаем HTTP сессию для работы с HTTP-запросами.
    # Задаем тайм-аут запроса
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as http_session:
        # Обрабатываем полученный список сообщений
        async for message in tqdm(messages_list, total=messages_list.left, desc='Processing ', ncols=100):
            # Определяем тип исходных сообщений
            source = SourceMessage(message_id=message.id, date=message.date, text=message.text)
            if source.message_type is None:
                message_types['unknown'] += 1
            details = []
            # Создаем детальные сообщения в зависимости от типа исходного сообщения
            match source.message_type:
                case 'vacancy':
                    # Разбиваем сообщение на отдельные вакансии
                    vacancies = re.split(config.get_vacancy_pattern(), source.text)
                    # Обрабатываем вакансии
                    for _ in vacancies:
                        vacancy = Vacancy(text=_, url='', html='')
                        if vacancy.text.strip(' *_\n'):
                            # Извлекаем URL вакансии
                            vacancy.url = re.search(config.get_url_pattern(), vacancy.text)[0]
                            # Получаем HTML-код страницы вакансии
                            try:
                                async with http_session.get(str(vacancy.url)) as response:
                                    match response.status:
                                        case 200:
                                            vacancy.html = await response.text()
                                        case 403 | 404 | 429:
                                            vacancy.html = HTTP_ERRORS.get(response.status)
                                        case _:
                                            vacancy.html = f'Error {response.status}'
                            except aiohttp.ClientError as e:
                                vacancy.html = f'Error {e}'
                            # Дописываем сообщение об ошибке доступа, если IP был заблокирован
                            if re.search(r'Your IP address.*?has been blocked', vacancy.html):
                                vacancy.html = f'{HTTP_ERRORS.get("IP blocked")}. {vacancy.html}'
                            # Сохраняем сообщение о вакансии в список
                            details.append(
                                VacancyMessage(source=source, text=vacancy.text.strip(' \n'),
                                               raw_html=vacancy.html.strip(' \n')))
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
    # Инициализируем счетчик типов сообщений
    message_types_counter: dict[str, int] = Counter()
    # Создание клиента для работы с Telegram
    client = (TelegramClient(session='.session',  # MemorySession(),
                             api_id=private_settings['APP_API_ID'],
                             api_hash=private_settings['APP_API_HASH']).start(private_settings['PHONE'],
                                                                              private_settings['PASSWORD']))
    with client:
        client.loop.run_until_complete(main(client, private_settings, message_types_counter))

    export_data_to_excel()
    print('   Report:')
    print(f'Vacancy:   {message_types_counter.get('vacancy', 0)}')
    print(f'Statistic: {message_types_counter.get('statistic', 0)}')
    print(f'Service:   {message_types_counter.get('service', 0)}')
    print(f'Unknown:   {message_types_counter.get('unknown', 0)}')

# TODO: Unit тесты
# TODO: Расписать проект в README
# TODO: продумать, как сделать с двуязычными комментариями и readme.md
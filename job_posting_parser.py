"""
The script implements the core logic of the project.

Variables are initialized:
private_settings: a dictionary containing confidential data for working with the Telegram API
message_types_counter: a counter for messages of all types
client: a Telegram client object
Functions:
load_env(file_path): a function for reading confidential data from a .env file for working with the Telegram API
async def main(client_telegram, priv_settings, message_types): an asynchronous function for retrieving and
processing messages from the Telegram chat
"""

from collections import Counter, namedtuple
import re
import aiohttp
from telethon import TelegramClient  # type: ignore
from tqdm.asyncio import tqdm
from database_handler import SourceMessage, VacancyMessage, StatisticMessage, ServiceMessage, \
    HTTP_ERRORS, session, config, export_data_to_excel


def load_env(file_path: str) -> dict:
    """
    Loading confidential data for working with the Telegram API from the `.env` file.
    Загрузка конфиденциальных данных для работы с Telegram API из файла .env

    Arguments:
    file_path (str): a confidential data file name
    Returns:
    dict: a confidential data dictionary
    """
    env_vars = {}
    with open(file_path, 'r', encoding='utf-8') as file_env:
        for line in file_env:
            if not line.strip().startswith('#') and '=' in line:
                key, value = line.strip().split('=')
                env_vars[key] = value
    return env_vars


# A tuple containing job posting data / Кортеж, который содержит данные вакансии
Vacancy = namedtuple('Vacancy', ['text', 'url', 'html'])


async def main(client_telegram, priv_settings, message_types):
    """
    Receiving and processing messages from a Telegram chat
    Получение и обработка сообщений из чата Telegram

    Arguments:
    client_telegram: a Telegram client object
    priv_settings: a confidential data dictionary for working with the Telegram API
    message_types: a counter for messages of all types
    """
    # Determine the ID of the last message in the database / Определяем ID последнего сообщения в базе данных
    last_message_id = 0
    if session.query(SourceMessage).count():
        last_message_id = max(map(lambda x: x[0], (session.query(SourceMessage.message_id))))
    # Retrieving new messages from the chat / Получаем новые сообщения из чата
    bot = await client_telegram.get_entity(priv_settings['BOT_NAME'])
    messages_list = client_telegram.iter_messages(bot.id, reverse=True, min_id=last_message_id, wait_time=0.1)
    print(f'   New messages: {messages_list.left}')
    # Set HTTP request timeout / Задаем тайм-аут HTTP запроса
    timeout = aiohttp.ClientTimeout(total=20)
    # Creating an HTTP session for handling HTTP requests / Создаем HTTP сессию для работы с HTTP-запросами
    async with aiohttp.ClientSession(timeout=timeout) as http_session:
        # Processing the received list of messages / Обрабатываем полученный список сообщений
        async for message in tqdm(messages_list, total=messages_list.left, desc='Processing ', ncols=100):
            # Determining the type of source messages / Определяем тип исходных сообщений
            source = SourceMessage(message_id=message.id, date=message.date, text=message.text)
            if source.message_type is None:
                message_types['unknown'] += 1
            details = []
            # Creating detailed messages based on the type of the source message
            # Создаем детальные сообщения в зависимости от типа исходного сообщения
            match source.message_type:
                case 'vacancy':
                    # Splitting the message into individual vacancies / Разбиваем сообщение на отдельные вакансии
                    vacancies = re.split(config.get_vacancy_pattern(), source.text)
                    # Processing vacancies / Обрабатываем вакансии
                    for _ in vacancies:
                        vacancy = Vacancy(text=_, url='', html='')
                        if vacancy.text.strip(' *_\n'):
                            # Extracting the job vacancy URL / Извлекаем URL вакансии
                            vacancy.url = re.search(config.get_url_pattern(), vacancy.text)[0]
                            # Retrieving the HTML code of the job vacancy page / Получаем HTML-код страницы вакансии
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
                            # Appending an access error message if the IP was blocked
                            # Дописываем сообщение об ошибке доступа, если IP был заблокирован
                            if re.search(r'Your IP address.*?has been blocked', vacancy.html):
                                vacancy.html = f'{HTTP_ERRORS.get("IP blocked")}. {vacancy.html}'
                            # Saving the vacancy message to the list of detailed messages
                            # Сохраняем сообщение о вакансии в список детальных сообщений
                            details.append(
                                VacancyMessage(source=source, text=vacancy.text.strip(' \n'),
                                               raw_html=vacancy.html.strip(' \n')))
                    message_types['vacancy'] += 1
                case 'statistic':
                    # Saving the statistics message to the list of detailed messages
                    # Сохраняем сообщение со статистикой в список детальных сообщений
                    details.append(StatisticMessage(source=source))
                    message_types['statistic'] += 1
                case 'service':
                    # Saving the service message to the list of detailed messages
                    # Сохраняем сервисное сообщение в список детальных сообщений
                    details.append(ServiceMessage(source=source))
                    message_types['service'] += 1
            # Writing the original and detailed messages to the session
            # Записываем исходное и детальные сообщения в сессию
            session.add(source)
            session.add_all(details)
            # Saving messages in the database / Сохраняем сообщения в базе данных
            session.commit()


if __name__ == '__main__':
    # Loading confidential Telegram API parameters / Загрузка конфиденциальных параметров Telegram API
    private_settings = load_env('.env')
    # Initializing the message counter for all types / Инициализация счетчика сообщений всех типов
    message_types_counter: dict[str, int] = Counter()
    # Creating a client for working with Telegram / Создание клиента для работы с Telegram
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
# TODO: продумать, как сделать демоверсию базы и экселя и как хранить настоящую, может переименовывать,
#  а обрезать в сервисе по дате - какой-то срок

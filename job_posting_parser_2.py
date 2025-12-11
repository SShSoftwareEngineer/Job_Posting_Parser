import asyncio
import hashlib
import json
from collections import Counter
from datetime import datetime

import aiohttp
from imapclient import IMAPClient
from sqlalchemy import select, func
from dotenv import dotenv_values
from telethon import TelegramClient
from tqdm import tqdm

from configs.config import GlobalConst, MessageSources, MessageTypes, VacancyAttrs
from database_handler import db_handler, RawMessage, Statistic, Service, VacancyWeb, Vacancy, VacancyData
import telegram_handler as tg_handler
from email_handler import get_email_list, init_imap_client
from parsers import TgRawParser, TgVacancyParser, TgStatisticParser, EmailRawParser, EmailVacancyParserVer0, \
    EmailVacancyParserVer1


def processing_telegram_messages(tg_client: TelegramClient, bot_name: str, messages_counter: Counter) -> Counter:
    """
    Receiving and processing new messages from a Telegram bot
    Получение и обработка новых сообщений из Telegram бота
    Attributes:
        tg_client (TelegramClient): Telegram client object
        bot_name (str): targeting Telegram bot name
        messages_counter (Counter): Message counter for all types of messages
    Returns:
        Counter: Updated message counter for all types
    """

    # Determine the last Telegram message date in the database / Определяем дату последнего Telegram сообщения в базе данных
    stmt = select(func.max(RawMessage.date)).where(RawMessage.message_source_id == MessageSources.TELEGRAM.value)
    last_date = db_handler.session.execute(stmt).scalar()
    # Retrieving new messages from the Telegram bot / Получаем новые сообщения из Telegram бота
    tg_messages = tg_handler.get_new_messages(tg_client, bot_name, last_date)
    # Updating the message types counter / Обновляем счетчик типов сообщений
    messages_counter[MessageSources.TELEGRAM.name] = len(tg_messages)
    # Processing the received list of messages / Обрабатываем полученный список сообщений
    desc = 'Processing Telegram messages'
    for message in tqdm(tg_messages, total=len(tg_messages), desc=desc, ncols=80 + len(desc)):
        # Parsing the raw Telegram message / Парсим исходное сообщение Telegram
        parsing_data = TgRawParser().parse(message=message)
        # tqdm.write(f'Processing message date: {parsing_data["date"]}')
        # Saving the raw message to the database / Сохраняем исходное сообщение в базе данных
        filter_fields = {'message_id': parsing_data['message_id']}
        # Removing unnecessary fields from parsing data / Убираем из данных парсинга ненужные поля
        del parsing_data['message_id']
        db_raw_message, added = db_handler.upsert_record(RawMessage, filter_fields, parsing_data)
        # Updating the message types counter / Обновляем счетчик типов сообщений
        messages_counter.update({f'TG_RAW {'added' if added else 'updated'}': 1})
        # Processing the message based on its type / Обрабатываем сообщения в зависимости от их типа
        match db_raw_message.message_type.name:
            case MessageTypes.TG_VACANCY.name:
                # Parsing the vacancy message / Парсим сообщение с вакансией
                parsing_data_list = TgVacancyParser().parse(text=db_raw_message.text)
                for data_number, parsing_data in enumerate(parsing_data_list):
                    # Creating or finding a job vacancy object on the site / Создаем или получаем объект объявления о вакансии на сайте
                    db_vacancy_web, added = db_handler.upsert_record(VacancyWeb,
                                                                     {'url': parsing_data.get(
                                                                         VacancyAttrs.URL.attr_id)}, {})
                    del parsing_data[VacancyAttrs.URL.attr_id]
                    # Updating the message URL's counter / Обновляем счетчик URL сообщений
                    messages_counter.update({f'TG_URL {'added' if added else 'updated'}': 1})
                    # Getting the hash value of the vacancy data to check for duplicates
                    # Получаем хэш параметров вакансии для проверки на дубликаты
                    json_str = json.dumps([db_raw_message.date.strftime('%d/%m/%Y %H:%M:%S'),
                                           db_raw_message.message_id, data_number], ensure_ascii=False)
                    hash_value = hashlib.md5(json_str.encode('utf-8')).hexdigest()
                    # Creating or finding a job vacancy object / Создаем или получаем объект вакансии
                    db_vacancy, added = db_handler.upsert_record(Vacancy, {'data_hash': hash_value},
                                                                 {'message_parsing_error': parsing_data.get(
                                                                     'message_parsing_error')})
                    del parsing_data['message_parsing_error']
                    # Updating the vacancy messages counter / Обновляем счетчик сообщений с вакансиями
                    messages_counter.update(
                        {f'{db_raw_message.message_type.name} {'added' if added else 'updated'}': 1})
                    # Добавляем связи вакансии
                    db_vacancy.vacancy_web.append(db_vacancy_web)
                    db_raw_message.vacancy.append(db_vacancy)
                    for attr_id, attr_value in parsing_data.items():
                        # Creating or finding a attribute vacancy object / Создаем или получаем объекты аттрибутов вакансии
                        db_attr, added = db_handler.upsert_record(VacancyData,
                                                                  {'attr_name_id': attr_id, 'attr_value': attr_value},
                                                                  {})
                        if db_attr not in db_vacancy.vacancy_data:
                            db_vacancy.vacancy_data.append(db_attr)

            case MessageTypes.TG_STATISTIC.name:
                # Parsing the statistic message / Парсим сообщение со статистикой
                parsing_data = TgStatisticParser().parse(text=db_raw_message.text)
                # Adding a link to the raw message
                # Добавляем связь с исходным сообщением
                parsing_data.update({'raw_message': db_raw_message})
                # Saving the statistic message to the database / Сохраняем сообщение со статистикой в базу данных
                db_statistic, added = db_handler.upsert_record(Statistic, {'raw_message_id': db_raw_message.id},
                                                               parsing_data)
                # Обновляем счетчик типов сообщений / Updating the message types counter
                messages_counter.update({f'{db_raw_message.message_type.name} {'added' if added else 'updated'}': 1})
            case MessageTypes.TG_SERVICE.name:
                # Saving the service message to the database / Сохраняем сервисное сообщение в базу данных
                db_service, added = db_handler.upsert_record(Service, {'raw_message_id': db_raw_message.id},
                                                             {'text': db_raw_message.text,
                                                              'raw_message': db_raw_message})
                # Обновляем счетчик типов сообщений / Updating the message types counter
                messages_counter.update({f'{db_raw_message.message_type.name} {'added' if added else 'updated'}': 1})
    return messages_counter


def processing_email_messages(imap_client: IMAPClient, folder_name: str, messages_counter: Counter) -> Counter:
    """
    Receiving and processing new messages from a IMAP Email client
    Получение и обработка новых сообщений из IMAP Email клиента
    Attributes:
        imap_client (IMAPClient): IMAPClient client object
        folder_name (str): targeting Email folder name
        messages_counter (Counter): Message counter for all types of messages
    Returns:
        Counter: Updated message counter for all types
    """

    # Processing the received list of messages / Обрабатываем полученный список сообщений

    # Determine the last Email message date in the database / Определяем дату последнего Email сообщения в базе данных
    stmt = select(func.max(RawMessage.date)).where(RawMessage.message_source_id == MessageSources.EMAIL.value)
    last_date = db_handler.session.execute(stmt).scalar()
    if last_date is None:
        last_date = datetime(2020, 1, 1).strftime('%d-%b-%Y')
    # Retrieving new emails  / Получаем новые сообщения электронной почты
    email_messages = get_email_list(imap_client=imap_client, folder_name=folder_name, last_date=last_date)
    # Обновляем счетчик типов сообщений / Updating the message types counter
    messages_counter[MessageSources.EMAIL.name] = len(email_messages)
    # Processing the received list of messages / Обрабатываем полученный список сообщений
    desc = 'Processing Email messages'
    for email_uid, message in tqdm(email_messages.items(), desc=desc, ncols=80 + len(desc)):
        # Parsing the raw Email message / Парсим исходное Email сообщение
        parsing_data = EmailRawParser().parse(email_uid=email_uid, email_body=message)
        # tqdm.write(f'Processing message date: {parsing_data["date"]}')
        # Saving the raw message to the database / Сохраняем исходное сообщение в базе данных
        filter_fields = {'email_uid': parsing_data['email_uid']}
        # Removing unnecessary fields from parsing data / Убираем из данных парсинга ненужные поля
        keys_to_delete = ['email_uid', 'from', 'subject', 'attachments']
        for key in keys_to_delete:
            parsing_data.pop(key, None)
        db_raw_message, added = db_handler.upsert_record(RawMessage, filter_fields, parsing_data)
        # Обновляем счетчик типов сообщений / Updating the message types counter
        messages_counter.update({f'EMAIL_RAW {'added' if added else 'updated'}': 1})
        # Processing the message based on its type / Обрабатываем сообщения в зависимости от их типа
        match db_raw_message.message_type.name:
            case MessageTypes.EMAIL_VACANCY.name:
                # Parsing the vacancy message / Парсим сообщение с вакансией
                if db_raw_message.date <= datetime(2025, 1, 24).astimezone():
                    parsing_data = EmailVacancyParserVer0().parse(html=db_raw_message.html)
                if db_raw_message.date > datetime(2025, 1, 24).astimezone():
                    parsing_data = EmailVacancyParserVer1().parse(html=db_raw_message.html)

                for data_number, parsing_data in enumerate(parsing_data):
                    # Creating or finding a job vacancy object on the site / Создаем или получаем объект объявления о вакансии на сайте
                    db_vacancy_web, added = db_handler.upsert_record(VacancyWeb, {'url': parsing_data.get(
                        VacancyAttrs.URL.attr_id)}, {})
                    del parsing_data[VacancyAttrs.URL.attr_id]
                    # Updating the message URL's counter / Обновляем счетчик URL сообщений
                    messages_counter.update({f'EMAIL_URL {'added' if added else 'updated'}': 1})
                    # Getting the hash value of the vacancy data to check for duplicates
                    # Получаем хэш параметров вакансии для проверки на дубликаты
                    json_str = json.dumps([db_raw_message.date.strftime('%d/%m/%Y %H:%M:%S'),
                                           db_raw_message.email_uid, data_number], ensure_ascii=False)
                    hash_value = hashlib.md5(json_str.encode('utf-8')).hexdigest()
                    # Creating or finding a job vacancy object / Создаем или получаем объект вакансии
                    db_vacancy, added = db_handler.upsert_record(Vacancy, {'data_hash': hash_value},
                                                                 {'message_parsing_error': parsing_data.get(
                                                                     'message_parsing_error')})
                    del parsing_data['message_parsing_error']
                    # Updating the vacancy messages counter / Обновляем счетчик сообщений с вакансиями
                    messages_counter.update(
                        {f'{db_raw_message.message_type.name} {'added' if added else 'updated'}': 1})
                    # Добавляем связи вакансии
                    db_vacancy.vacancy_web.append(db_vacancy_web)
                    db_raw_message.vacancy.append(db_vacancy)
                    for attr_id, attr_value in parsing_data.items():
                        # Creating or finding a attribute vacancy object / Создаем или получаем объекты аттрибутов вакансии
                        db_attr, added = db_handler.upsert_record(VacancyData,
                                                                  {'attr_name_id': attr_id, 'attr_value': attr_value},
                                                                  {})
                        if db_attr not in db_vacancy.vacancy_data:
                            db_vacancy.vacancy_data.append(db_attr)
    return messages_counter


async def fetch_html(session, url):
    """
    Получение HTML одной страницы
    """

    result = {'url': url}
    try:
        async with session.get(url, timeout=GlobalConst.timeout_seconds) as response:
            if response.status == 200:
                html_content = await response.text()
                result.update({'status': response.status, 'html': html_content})
            else:
                result.update({'status': response.status, 'html': f'Not OK status for URL {url}: {response.status}'})
    except (aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError, asyncio.TimeoutError) as e:
        result.update({'status': 'Error', 'html': f'Connection error/timeout: {type(e).__name__}'})
    except Exception as e:
        result.update({'status': 'Error', 'html': f"Unknown error fetching URL {url}: {e}"})
    return result


async def fetch_all(urls, max_concurrent=GlobalConst.max_concurrent_requests):
    """
    Получение HTML нескольких страниц с ограничением по количеству одновременных запросов
    """

    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_sem(_session, url):
        async with semaphore:
            return await fetch_html(_session, url)

    async with aiohttp.ClientSession() as http_session:
        tasks = [fetch_with_sem(http_session, url) for url in urls]
        return await asyncio.gather(*tasks)


def processing_web_vacancy(messages_counter: Counter) -> Counter:
    """
    Receiving and processing new vacancy messages from a web site
    Получение и обработка новых сообщений о вакансиях с сайта
    """

    stmt = select(VacancyWeb.url).where(VacancyWeb.raw_html.is_(None)).limit(10)
    urls = db_handler.session.execute(stmt).scalars().all()
    web_vacancies = asyncio.run(fetch_all(urls))
    desc = 'Processing Website vacancies'
    for web_vacancy in tqdm(web_vacancies, total=len(web_vacancies), desc=desc, ncols=80 + len(desc)):
        # Parsing the website vacancy message / Парсим сообщение о вакансии с сайта

        pass

    return messages_counter


def main():
    # Loading confidential Telegram API parameters / Загрузка конфиденциальных параметров Telegram API
    private_settings = dotenv_values(GlobalConst.private_settings_file)
    # Initializing the message counter for all types / Инициализация счетчика сообщений всех типов
    messages_counter = Counter()

    # Creating a client for working with Telegram / Создание клиента для работы с Telegram
    tg_client = tg_handler.init_tg_client(private_settings['APP_API_ID'], private_settings['APP_API_HASH'],
                                          private_settings['PHONE'], private_settings['TELEGRAM_PASSWORD'])
    # Retrieving, processing and saving to database new Telegram messages
    # Получение, обработка и сохранение в базе данных новых сообщений Telegram
    with db_handler.session.begin():
        messages_counter = processing_telegram_messages(tg_client, private_settings['BOT_NAME'], messages_counter)
    tg_handler.cleanup_loop()

    print('   Report:')
    for item in sorted(messages_counter.items()):
        print(f'{item[0]:20} {item[1]}')

    # Creating a client for working with IMAP / Создание клиента для работы с IMAP
    imap_client = init_imap_client(private_settings['IMAP_HOST'], int(private_settings['IMAP_PORT']), 10,
                                   private_settings['USERNAME'], private_settings['IMAP_PASSWORD'])
    # Retrieving, processing and saving to database new Email messages
    # Получение, обработка и сохранение в базе данных новых Email сообщений
    with db_handler.session.begin():
        messages_counter = processing_email_messages(imap_client, private_settings['FOLDER_NAME'], messages_counter)

    print('   Report:')
    for item in sorted(messages_counter.items()):
        print(f'{item[0]:20} {item[1]}')

    # Получение, обработка и сохранение в базе данных новых сообщений о вакансиях с сайта

    messages_counter = processing_web_vacancy(messages_counter)


if __name__ == '__main__':
    main()

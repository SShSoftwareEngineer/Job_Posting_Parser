"""
Main script for receiving, processing and saving job posting messages from Telegram bot, Email and web site to database
Основной скрипт для получения, обработки и сохранения в БД сообщений о вакансиях из Telegram бота, Email и с сайта
"""

import asyncio
import hashlib
import http
import json
from collections import Counter
from datetime import datetime

import aiohttp
from imapclient import IMAPClient
from sqlalchemy import select, func, or_, and_
from dotenv import dotenv_values
from telethon import TelegramClient
from tqdm import tqdm

from configs.config import GlobalConst, MessageSources, MessageTypes, VacancyAttrs
from database_handler import db_handler, RawMessage, Statistic, Service, VacancyWeb, Vacancy, VacancyData
import telegram_handler as tg_handler
from email_handler import get_email_list, init_imap_client
from parsers import TgRawParser, TgVacancyParser, TgStatisticParser, EmailRawParser, EmailVacancyParserVer0, \
    EmailVacancyParserVer1, WebVacancyParser


def telegram_messages_processing(tg_client: TelegramClient, bot_name: str, from_first: bool,
                                 messages_counter: Counter) -> Counter:
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

    # Determine the last Telegram message date in the database / Определяем дату последнего Telegram сообщения в БД
    stmt = select(func.max(RawMessage.date)).where(RawMessage.message_source_id == MessageSources.TELEGRAM.value)
    last_date = db_handler.session.execute(stmt).scalar()
    if any([last_date is None, from_first]):
        last_date = GlobalConst.start_date
    # Retrieving new messages from the Telegram bot / Получаем новые сообщения из Telegram бота
    print(f'Retrieving new Telegram messages since {last_date.strftime('%d-%b-%Y')}...')
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
                    # Creating or finding a job vacancy object on the site
                    # Создаем или получаем экземпляр объявления о вакансии на сайте
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
                        # Creating or finding a attribute vacancy object
                        # Создаем или получаем объекты аттрибутов вакансии
                        db_attr, added = db_handler.upsert_record(VacancyData,
                                                                  {'attr_name_id': attr_id, 'attr_value': attr_value},
                                                                  {'attr_source_id': MessageSources.TELEGRAM.value})
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


def email_messages_processing(imap_client: IMAPClient, folder_name: str, from_first: bool,
                              messages_counter: Counter) -> Counter:
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
    if any([last_date is None, from_first]):
        last_date = GlobalConst.start_date.strftime('%d-%b-%Y')
    # Retrieving new email messages / Получаем новые сообщения электронной почты
    print(f'Retrieving new Email messages since {last_date}...')
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
                # До 24.01.2025 старый формат Email сообщений
                if db_raw_message.date <= datetime(2025, 1, 24).astimezone():
                    parsing_data = EmailVacancyParserVer0().parse(html=db_raw_message.html)
                # С 24.01.2025 новый формат Email сообщений
                if db_raw_message.date > datetime(2025, 1, 24).astimezone():
                    parsing_data = EmailVacancyParserVer1().parse(html=db_raw_message.html)
                for data_number, parsing_data in enumerate(parsing_data):
                    # Creating or finding a job vacancy object on the site
                    # Создаем или получаем объект объявления о вакансии на сайте
                    db_vacancy_web, added = db_handler.upsert_record(VacancyWeb, {'url': parsing_data.get(
                        VacancyAttrs.URL.attr_id)}, {})
                    # Если вакансия обновлена, обнуляем HTML вакансии на сайте для последующего перезапроса и разбора
                    if not added:
                        db_vacancy_web.raw_html = None
                        db_vacancy_web.status_code = None
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
                        # Creating or finding a attribute vacancy object
                        # Создаем или получаем объекты аттрибутов вакансии
                        db_attr, added = db_handler.upsert_record(VacancyData,
                                                                  {'attr_name_id': attr_id, 'attr_value': attr_value},
                                                                  {'attr_source_id': MessageSources.EMAIL.value})
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
            if response.status == http.HTTPStatus.OK:
                html_content = await response.text()
                result.update({'status': response.status, 'html': html_content.strip()})
            else:
                result.update({'status': response.status, 'html': f'Error for URL {url}: {response.status}'})
    except (aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError, asyncio.TimeoutError) as e:
        result.update({'status': 0, 'html': f'Connection error/timeout: {type(e).__name__}'})
    except Exception as e:
        result.update({'status': 0, 'html': f"Unknown error fetching URL {url}: {e}"})
    return result


async def fetch_all(urls, max_concurrent=GlobalConst.max_concurrent_requests):
    """
    Получение HTML нескольких страниц с ограничением по количеству одновременных запросов
    """

    semaphore = asyncio.Semaphore(max_concurrent)
    headers = {'User-Agent': GlobalConst.user_agent}

    async def fetch_with_sem(_session, url):
        async with semaphore:
            return await fetch_html(_session, url)

    async with aiohttp.ClientSession(headers=headers) as http_session:
        tasks = [fetch_with_sem(http_session, url) for url in urls]
        return await asyncio.gather(*tasks)


def web_vacancy_fetching(messages_counter: Counter) -> Counter:
    """
    Receiving new vacancy posting from a web site
    Получение новых сообщений о вакансиях с сайта
    """

    # Retrieving URLs of vacancies that need to be checked / Получаем URL вакансий, которые нужно проверить
    print('Retrieving URLs of vacancies that need to be checked')
    stmt = select(VacancyWeb.url).where(or_(VacancyWeb.raw_html.is_(None),
                                            VacancyWeb.status_code.notin_([http.HTTPStatus.NOT_FOUND,
                                                                           http.HTTPStatus.OK])), )
    urls = db_handler.session.execute(stmt).scalars().all()
    # Retrieving HTML of vacancy pages / Получаем HTML страниц вакансий
    web_vacancies = asyncio.run(fetch_all(urls))
    for web_vacancy in web_vacancies:
        filter_fields = {'url': web_vacancy['url']}
        # Заменяем статус для заблокированных запросов на 429
        if 'Your IP address' in web_vacancy.get('html') and 'has been blocked' in web_vacancy.get('html'):
            web_vacancy['status'] = http.HTTPStatus.TOO_MANY_REQUESTS  # 429 IP blocked
        # Обновляем HTML страницы для проверенных URL
        update_fields = {'raw_html': web_vacancy.get('html'),
                         'last_check': datetime.now(),
                         'status_code': web_vacancy.get('status'),
                         'parsing_date': None}
        db_vacancy_web, added = db_handler.upsert_record(VacancyWeb, filter_fields, update_fields)
        # Updating the message URL's counter / Обновляем счетчик URL сообщений
        messages_counter.update({f'WEB_URL {'added' if added else 'updated'}': 1})
    return messages_counter


def web_vacancy_parsing(from_date: datetime | None, messages_counter: Counter) -> Counter:
    """
    Parsing new vacancy messages from a web site
    Парсинг новых сообщений о вакансиях с сайта
    """

    if from_date is None:
        from_date = GlobalConst.start_date.replace(year=GlobalConst.start_date.year + 1000)
    stmt = (select(VacancyWeb, Vacancy, RawMessage.date)
            .join(Vacancy, VacancyWeb.vacancy_id == Vacancy.id)
            .join(RawMessage, Vacancy.raw_message_id == RawMessage.id)
            ).where(and_(VacancyWeb.status_code == http.HTTPStatus.OK,
                         or_(VacancyWeb.parsing_date.is_(None),
                             VacancyWeb.parsing_date < VacancyWeb.last_check,
                             RawMessage.date >= from_date)),
                    ).order_by(RawMessage.date)
    processing_items = db_handler.session.execute(stmt).mappings().all()
    desc = 'Processing Website job posting'
    for item in tqdm(processing_items, desc=desc, ncols=80 + len(desc)):
        db_vacancy_web = item.get('VacancyWeb')
        db_vacancy = item.get('Vacancy')
        parsing_data = WebVacancyParser().parse(html=db_vacancy_web.raw_html)
        # Результаты парсинга записываем отдельно в таблицу вакансий
        db_vacancy.web_parsing_error = parsing_data.pop('web_parsing_error', None)
        # URL из результатов парсинга записываем отдельно в таблицу веб-вакансий
        db_vacancy_web.url = parsing_data.pop(VacancyAttrs.URL.attr_id, None)
        # Добавляем в БД и к соответствующим вакансиям атрибуты вакансий
        for attr_id, attr_value in parsing_data.items():
            # Creating or finding a attribute vacancy object / Создаем или получаем объекты аттрибутов вакансии
            db_attr, added = db_handler.upsert_record(VacancyData,
                                                      {'attr_name_id': attr_id, 'attr_value': attr_value},
                                                      {'attr_source_id': MessageSources.WEB.value})
            if db_attr not in db_vacancy.vacancy_data:
                db_vacancy.vacancy_data.append(db_attr)
        db_vacancy_web.parsing_date = datetime.now().astimezone()
        # Updating the vacancy messages counter / Обновляем счетчик сообщений с вакансиями
        messages_counter.update({'WEB_VACANCY_PARSED': 1})
    return messages_counter


def main():
    """
    Main function for receiving, processing and saving job posting messages from Telegram, Email and web site to the DB
    Основная функция для получения, обработки и сохранения в БД сообщений о вакансиях из Telegram бота, Email и c сайта
    Returns:
        None
    """

    # Loading confidential Telegram API parameters / Загрузка конфиденциальных параметров Telegram API
    private_settings = dotenv_values(GlobalConst.private_settings_file)
    # Initializing the message counter for all types / Инициализация счетчика сообщений всех типов
    messages_counter = Counter()

    # # Creating a client for working with Telegram / Создание клиента для работы с Telegram
    # tg_client = tg_handler.init_tg_client(int(private_settings['APP_API_ID']), private_settings['APP_API_HASH'],
    #                                       private_settings['PHONE'], private_settings['TELEGRAM_PASSWORD'])
    # # Retrieving, processing and saving to database new Telegram messages
    # # Получение, обработка и сохранение в базе данных новых сообщений Telegram
    # with db_handler.session.begin():
    #     messages_counter = telegram_messages_processing(tg_client, private_settings['BOT_NAME'], False,
    #                                                     messages_counter)
    # tg_handler.cleanup_loop(tg_client)

    # Creating a client for working with IMAP / Создание клиента для работы с IMAP
    imap_client = init_imap_client(private_settings['IMAP_HOST'], int(private_settings['IMAP_PORT']), 10,
                                   private_settings['USERNAME'], private_settings['IMAP_PASSWORD'])
    # Retrieving, processing and saving to database new Email messages
    # Получение, обработка и сохранение в базе данных новых Email сообщений
    with db_handler.session.begin():
        messages_counter = email_messages_processing(imap_client, private_settings['FOLDER_NAME'], False,
                                                     messages_counter)

    # Получение, обработка и сохранение в базе данных новых сообщений о вакансиях с сайта
    with db_handler.session.begin():
        messages_counter = web_vacancy_fetching(messages_counter)
    with db_handler.session.begin():
        # parse_from_date = None
        parse_from_date = datetime(2020, 1, 1)
        messages_counter = web_vacancy_parsing(from_date=parse_from_date, messages_counter=messages_counter)

    print()
    print('   Report:')
    for item in sorted(messages_counter.items()):
        print(f'{item[0]:21} {item[1]}')


if __name__ == '__main__':
    main()

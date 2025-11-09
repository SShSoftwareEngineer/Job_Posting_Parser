import hashlib
import json
from collections import Counter
from datetime import datetime
from sqlalchemy import select, func
from dotenv import dotenv_values
from configs.config import GlobalConst, MessageSources, MessageTypes
from database_handler import db_handler, RawMessage, Vacancy, Statistic, Service, VacancyWeb
import telegram_handler as tg_handler
from email_handler import get_email_list
from parsers import TgRawMessageParser, TgVacancyTextParser, TgStatisticTextParser


def get_telegram_messages(private_settings: dict, messages_counter: Counter) -> Counter:
    # Creating a client for working with Telegram / Создание клиента для работы с Telegram
    tg_client = tg_handler.init_tg_client(private_settings['APP_API_ID'], private_settings['APP_API_HASH'],
                                          private_settings['PHONE'], private_settings['TELEGRAM_PASSWORD'])
    # Determine the last Telegram message date in the database / Определяем дату последнего Telegram сообщения в базе данных
    stmt = select(func.max(RawMessage.date)).where(RawMessage.message_source_id == MessageSources.TELEGRAM.value)
    last_date = db_handler.session.execute(stmt).scalar()
    if last_date is None:
        last_date = datetime(1970, 1, 1)
    # Retrieving new messages from the Telegram bot / Получаем новые сообщения из Telegram бота
    tg_messages = tg_handler.get_new_messages(tg_client, private_settings['BOT_NAME'], last_date)
    messages_counter[MessageSources.TELEGRAM.name] = len(tg_messages)
    # Processing the received list of messages / Обрабатываем полученный список сообщений
    for message in tg_messages:
        # Parsing the raw Telegram message / Парсим исходное сообщение Telegram
        parsing_data = TgRawMessageParser().parse(message=message)
        # Saving the raw message to the database / Сохраняем исходное сообщение в базе данных
        filter_fields = {'message_id': parsing_data['message_id']}
        del parsing_data['message_id']
        db_raw_message, added = db_handler.upsert_record(RawMessage, filter_fields, parsing_data)
        # Обновляем счетчик типов сообщений / Updating the message types counter
        if added:
            messages_counter.update({'TG_RAW': 1})
        match db_raw_message.message_type.name:
            case MessageTypes.TG_VACANCY.name:
                # Parsing the vacancy message / Парсим сообщение с вакансией
                parsing_data = TgVacancyTextParser().parse(text=db_raw_message.text)
                # Создаем объект объявления о вакансии на сайте / Creating a job vacancy object on the site
                db_vacancy_web, added = db_handler.upsert_record(VacancyWeb, {'url': parsing_data['url']}, {})
                del parsing_data['url']
                # Обновляем счетчик типов сообщений / Updating the message types counter
                if added:
                    messages_counter.update({'TG_URL': 1})
                # Getting the hash value of the vacancy data to check for duplicates
                # Получаем хэш параметров вакансии для проверки на дубликаты
                json_str = json.dumps(parsing_data, sort_keys=True, ensure_ascii=False)
                hash_value = hashlib.md5(json_str.encode('utf-8')).hexdigest()
                # Saving the vacancy message to the database / Сохраняем сообщение с вакансией в базу данных
                db_vacancy, added = db_handler.upsert_record(Vacancy, {'text_data_hash': hash_value}, parsing_data)
                db_vacancy.vacancy_web.append(db_vacancy_web)
                db_raw_message.vacancy.append(db_vacancy)
                # Обновляем счетчик типов сообщений / Updating the message types counter
                if added:
                    messages_counter.update({db_raw_message.message_type.name: 1})
            case MessageTypes.TG_STATISTIC.name:
                # Parsing the statistic message / Парсим сообщение со статистикой
                parsing_data = TgStatisticTextParser().parse(text=db_raw_message.text)
                # Adding a link to the raw message
                # Добавляем связь с исходным сообщением
                parsing_data.update({'raw_message': db_raw_message})
                # Saving the statistic message to the database / Сохраняем сообщение со статистикой в базу данных
                db_statistic, added = db_handler.upsert_record(Statistic, {'raw_message_id': db_raw_message.id},
                                                               parsing_data)
                # Обновляем счетчик типов сообщений / Updating the message types counter
                if added:
                    messages_counter.update({db_raw_message.message_type.name: 1})
            case MessageTypes.TG_SERVICE.name:
                # Saving the service message to the database / Сохраняем сервисное сообщение в базу данных
                db_service, added = db_handler.upsert_record(Service, {'raw_message_id': db_raw_message.id}, {})
                # Обновляем счетчик типов сообщений / Updating the message types counter
                if added:
                    messages_counter.update({db_raw_message.message_type.name: 1})
        db_handler.session.commit()
    return messages_counter


def get_email_messages():
    pass


def main():
    # Loading confidential Telegram API parameters / Загрузка конфиденциальных параметров Telegram API
    private_settings = dotenv_values(GlobalConst.private_settings_file)
    # Initializing the message counter for all types / Инициализация счетчика сообщений всех типов
    messages_counter = Counter()
    # Retrieving and processing new Telegram messages / Получение и обработка новых сообщений Telegram
    get_telegram_messages(private_settings, messages_counter)

    print('messages_counter:', messages_counter)

    # # Determine the last Email message date in the database / Определяем дату последнего Email сообщения в базе данных
    # stmt = select(func.max(RawMessage.date)).where(RawMessage.message_source_id == MessageSources.EMAIL.value)
    # last_date = db_handler.session.execute(stmt).scalar()
    # if last_date is None:
    #     last_date = datetime(1970, 1, 1)
    #
    # last_date = datetime(2025, 10, 15).strftime('%d-%b-%Y')
    #
    # # Retrieving new emails  / Получаем новые сообщения электронной почты
    # email_messages = get_email_list(host=private_settings['IMAP_HOST'],
    #                                 port=int(private_settings['IMAP_PORT']),
    #                                 username=private_settings['USERNAME'],
    #                                 password=private_settings['IMAP_PASSWORD'],
    #                                 folder_name=private_settings['FOLDER_NAME'],
    #                                 since_date=last_date)
    # # Processing the received list of emails / Обрабатываем полученный список сообщений электронной почты
    # types_counter[MessageSources.EMAIL.name] = len(email_messages)
    # # Processing the received list of messages / Обрабатываем полученный список сообщений
    # for message in email_messages:
    #     pass


if __name__ == '__main__':
    main()

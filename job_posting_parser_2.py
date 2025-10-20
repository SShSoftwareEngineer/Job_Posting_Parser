from collections import Counter
from datetime import datetime
from sqlalchemy import select, func

from configs.config import GlobalConst, MessageSources, MessageTypes
from utils import load_env
from database_handler import db_handler, RawMessage
import telegram_handler as tg_handler
from email_handler import get_email_list


class MessageProcessor:
    tg_message_id: int
    date: datetime
    text: str | None
    message_type: str | None

    def type_define(self):
        pass


def main():
    # Loading confidential Telegram API parameters / Загрузка конфиденциальных параметров Telegram API
    private_settings = load_env(GlobalConst.private_settings_file)
    # Creating a client for working with Telegram / Создание клиента для работы с Telegram
    tg_client = tg_handler.init_tg_client(private_settings['APP_API_ID'], private_settings['APP_API_HASH'],
                                          private_settings['PHONE'], private_settings['TELEGRAM_PASSWORD'])
    # Initializing the message counter for all types / Инициализация счетчика сообщений всех типов
    types_counter: dict[str, int] = Counter()
    # Determine the last Telegram message date in the database / Определяем дату последнего Telegram сообщения в базе данных
    stmt = select(func.max(RawMessage.date)).where(RawMessage.message_source == MessageSources.Telegram.value)
    last_date = db_handler.session.execute(stmt).scalar_one_or_none()
    if last_date is None:
        last_date = datetime(1970, 1, 1)
    # Retrieving new messages from the Telegram bot / Получаем новые сообщения из Telegram бота

    last_date = datetime(2025, 10, 10)

    tg_messages = tg_handler.get_new_messages(tg_client, private_settings['BOT_NAME'], last_date)
    types_counter[MessageSources.Telegram.name] = len(tg_messages)
    # Processing the received list of messages / Обрабатываем полученный список сообщений
    for message in tg_messages:
        pass

    # Determine the last Email message date in the database / Определяем дату последнего Email сообщения в базе данных
    stmt = select(func.max(RawMessage.date)).where(RawMessage.message_source == MessageSources.Email.value)
    last_date = db_handler.session.execute(stmt).scalar_one_or_none()
    if last_date is None:
        last_date = datetime(1970, 1, 1)

    last_date = datetime(2025, 10, 10).strftime('%d-%b-%Y')

    # Retrieving new emails  / Получаем новые сообщения электронной почты
    email_messages = get_email_list(host=private_settings['IMAP_HOST'],
                                    port=int(private_settings['IMAP_PORT']),
                                    username=private_settings['USERNAME'],
                                    password=private_settings['IMAP_PASSWORD'],
                                    folder_name=private_settings['FOLDER_NAME'],
                                    since_date=last_date)
    # Processing the received list of emails / Обрабатываем полученный список сообщений электронной почты
    types_counter[MessageSources.Email.name] = len(email_messages)
    # Processing the received list of messages / Обрабатываем полученный список сообщений
    for message in email_messages:
        pass


if __name__ == '__main__':
    main()

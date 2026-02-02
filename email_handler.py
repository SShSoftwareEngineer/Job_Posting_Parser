"""
Module for working with IMAP Email
Модуль для работы с IMAP Email
"""

from email.header import decode_header
from imapclient import IMAPClient


def init_imap_client(host: str, port: int, timeout: float, username: str, password: str) -> IMAPClient:
    """
    Initializes IMAP Email client
    Инициализирует клиент IMAP Email
    Attributes:
        host (str): IMAP server host.
        port (int): IMAP server port.
        timeout (float): Connection timeout in seconds.
        username (str): Username for authentication.
        password (str): Password for authentication.
    Returns:
        IMAPClient: Initialized IMAP client.
    """

    imap_client = IMAPClient(host=host, port=port, use_uid=True, timeout=timeout)
    imap_client.login(username=username, password=password)
    return imap_client


def decode_email_field(field_value):
    """
    Function for decoding email fields
    Функция декодирования полей письма
    Attributes:
        field_value: Encoded email field value.
    Returns:
        Decoded email field value as a string.
    """

    if not field_value:
        return ''
    decoded = ''
    for email_part, encoding in decode_header(field_value):
        if isinstance(email_part, bytes):
            decoded += email_part.decode(encoding or 'utf-8', errors='ignore')
        else:
            decoded += str(email_part)
    return decoded


def get_email_list(imap_client: IMAPClient, folder_name: str, last_date: str) -> dict:
    """
    Получение списка писем из IMAP Email аккаунта
    Function to get a list of emails from an IMAP Email account
    Attributes:
        imap_client (IMAPClient): Initialized IMAP client.
        folder_name (str): Name of the email folder to fetch emails from.
        last_date (str): Date string in format 'DD-Mon-YYYY' to filter emails since that date.
    Returns:
        dict: Dictionary containing email data.
    """

    with imap_client as client:
        client.select_folder(folder_name)
        # Receiving a list of email UIDs / Получаем список UID писем
        email_uids = client.search(['SINCE', last_date])
        # Receiving the bodies of letters / Получаем тела писем
        emails_list = client.fetch(email_uids, [
            'ENVELOPE',  # From whom, subject, date / От кого, тема, дата
            'FLAGS',  # Flags (read, important, etc.) / Флаги (прочитано, важное и т.д.)
            'RFC822.SIZE',  # Letter size / Размер письма
            'RFC822'  # Body (full letter) / Тело (полное письмо)
        ])
    return emails_list


if __name__ == '__main__':
    pass

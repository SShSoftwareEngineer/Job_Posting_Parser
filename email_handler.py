from email.header import decode_header
from imapclient import IMAPClient


def init_imap_client(host: str, port: int, timeout: float, username: str, password: str) -> IMAPClient:
    """
    Инициализирует клиент IMAP Email
    """

    global _imap_client
    _imap_client = IMAPClient(host=host, port=port, use_uid=True, timeout=timeout)
    _imap_client.login(username=username, password=password)
    return _imap_client


def decode_email_field(field_value):
    """
    Функция декодирования полей письма
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
    """

    with imap_client as client:
        client.select_folder(folder_name)
        # Получаем список UID писем
        email_uids = client.search([u'SINCE', last_date])
        # Получаем тела писем
        emails_list = client.fetch(email_uids, [
            'ENVELOPE',  # От кого, тема, дата
            'FLAGS',  # Флаги (прочитано, важное и т.д.)
            'RFC822.SIZE',  # Размер письма
            'RFC822'  # Тело (полное письмо)
        ])
    return emails_list




# Creating a client for working with IMAP Email / Создание клиента для работы с IMAP Email
_imap_client = None

if __name__ == '__main__':
    pass

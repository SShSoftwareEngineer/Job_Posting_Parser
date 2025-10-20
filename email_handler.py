from email.header import decode_header
from typing import cast

from imapclient import IMAPClient
from email import message_from_bytes, policy
from email.message import EmailMessage


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


def get_email_list(host: str, port: int, username: str, password: str, folder_name: str, since_date: str):
    with IMAPClient(host=host, port=port, use_uid=True) as client:
        client.login(username=username, password=password)
        client.select_folder(folder_name)
        # Получаем список ID писем
        email_ids = client.search([u'SINCE', since_date])
        # Получаем тела писем
        emails_list = client.fetch(email_ids, ['RFC822'])
    return emails_list


def get_email_data(email_uid: int, email_body: dict):
    email_message = cast(EmailMessage, message_from_bytes(email_body[b'RFC822'], policy=policy.default))
    # Парсим письмо и извлекаем текст и вложения
    email_data = {
        'id': email_uid,
        'from': decode_email_field(email_message['From']),
        'subject': decode_email_field(email_message['Subject']),
        'date': email_message['Date'],
        'text': '',
        'html': '',
        'attachments': []
    }
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                email_data['text'] = part.get_content()
            elif content_type == 'text/html':
                email_data['html'] = part.get_content()
            elif part.get_content_disposition() == 'attachment':
                email_data['attachments'].append({
                    'filename': part.get_filename(),
                    'content': part.get_content()
                })
    else:
        try:
            content = email_message.get_content()
            content_type = email_message.get_content_type()
            if content_type == 'text/html':
                email_data['html'] = content
            else:
                email_data['text'] = content
        except (KeyError, AttributeError, UnicodeDecodeError, LookupError) as err:
            # Ловим конкретные ошибки, которые могут возникнуть
            print(err.__class__.__name__, str(err))
            payload = email_message.get_payload(decode=True)
            if isinstance(payload, bytes):
                email_data['text'] = payload.decode('utf-8', errors='ignore')
            else:
                email_data['text'] = str(payload)
    return email_data


if __name__ == '__main__':
    pass

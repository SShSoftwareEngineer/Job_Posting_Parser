import re
from abc import ABC, abstractmethod
from email import message_from_bytes, policy
from email.message import EmailMessage
from typing import cast

from telethon.tl.types import Message

from config_handler import tg_vacancy_text_signs, regex_patterns, tg_statistic_text_signs
from configs.config import MessageSources
from email_handler import decode_email_field, email_detect_message_type
from telegram_handler import tg_detect_message_type
from utils import str_to_numeric, parse_date_string


class MessageParser(ABC):
    """
    Абстрактный класс, возвращает словарь с результатами парсинга
    """

    @abstractmethod
    def parse(self, **options) -> dict:
        pass


class TgRawMessageParser(MessageParser):
    """
    Класс для парсинга исходных сообщений Telegram, возвращает словарь с результатами парсинга
    """

    def parse(self, message: Message) -> dict:
        """
        Функция для парсинга исходных сообщений Telegram, возвращает словарь с результатами парсинга
        """

        if hasattr(message, 'text'):
            message_text = message.text
        elif hasattr(message, 'raw_message'):
            message_text = message.raw_message
        elif hasattr(message, 'message'):
            message_text = message.message
        else:
            message_text = ''
        message_type = tg_detect_message_type(message_text)
        parsed_data = {
            'date': message.date.astimezone(),
            'message_id': message.id,
            'email_uid': None,
            'text': message_text,
            'message_source_id': MessageSources.TELEGRAM.value,
            'message_type_id': message_type.get_message_type_id(message_type),
        }
        # Подсчет успешно распарсенных полей / Counting successfully parsed fields
        parsed_fields = ['date', 'message_id', 'text']
        unsuccessfully_parsed_fields = [field for field in parsed_fields if parsed_data.get(field) is None]
        if unsuccessfully_parsed_fields:
            parsed_data['parsing_error'] = (f'{len(unsuccessfully_parsed_fields)} | {len(parsed_fields)},'
                                            f' {', '.join(unsuccessfully_parsed_fields)}')
        return parsed_data


class TgVacancyTextParser(MessageParser):
    """
    Класс для парсинга сообщений Telegram с вакансиями, возвращает словарь с результатами парсинга
    """

    @staticmethod
    def vacancy_split(text: str) -> list[str]:
        """
        Функция для разделения текста сообщения Telegram с вакансиями на отдельные части по двойным переносам строк
        """

        text = text.replace('\n\n', 'Possible_Vacancy_Splitter')
        pattern = fr'((?:{"|".join(tg_vacancy_text_signs.splitter_pattern)}).*?)(Possible_Vacancy_Splitter)'
        text = re.sub(pattern, r'\1\n\n', text)
        text = text.replace('Possible_Vacancy_Splitter', '\n')
        return text.split('\n\n')

    def parse(self, text: str) -> list[dict]:
        """
        Функция для парсинга списка сообщений Telegram с вакансиями, возвращает список словарей с результатами парсинга
        """

        # Разделение текста сообщения Telegram с несколькими вакансиями на отдельные части по двойным переносам строк
        text_parts = self.vacancy_split(text)
        parsed_vacancies_data = []
        # Обработка каждой части текста сообщения Telegram с вакансией
        for text_part in text_parts:
            text_part=text_part.replace('\n\n', '\n').strip()
            parsed_data = {'text': text_part}
            # Извлечение строк с необходимой информацией / Extracting lines with the necessary information
            strings = text_part.split('\n')
            str_1 = re.sub(r'[*_`]+', '', strings[0]).replace('  ', ' ')
            str_2 = re.sub(r'[*_`]+', '', strings[1]).replace('  ', ' ')
            str_last = re.sub(r'[*_`]+', '', strings[-1]).replace('  ', ' ')
            # Extracting the position and company name from the Telegram message text
            # Извлечение позиции, названия компании из текста сообщения Telegram
            matching = re.split(f"{'|'.join(tg_vacancy_text_signs.position_company)}", str_1)
            if matching:
                parsed_data['position_msg'] = matching[0]
                if len(matching) > 1:
                    parsed_data['company'] = matching[1]
            else:
                parsed_data['position_msg'] = str_1
            # Extracting the company location and experience requirements from the Telegram message text
            # Извлечение локации компании, опыта работы из текста сообщения Telegram
            matching = re.search(
                f'(.+), {regex_patterns.numeric}? ?({"|".join(tg_vacancy_text_signs.location_experience)})', str_2)
            if matching:
                parsed_data['location'] = matching.group(1)
                parsed_data['experience_msg'] = cast(int | None, str_to_numeric(matching.group(2)))
                if matching.group(2) is None and matching.group(3) is not None:
                    parsed_data['experience_msg'] = 0
            # Extracting salary information from the Telegram message text
            # Извлечение информации о зарплате из текста сообщения Telegram
            matching = re.search(fr'{regex_patterns.salary_range}\Z', str_2)
            if matching:
                if len(matching.groups()) == 2:
                    parsed_data['min_salary'] = cast(int | None, str_to_numeric(matching.groups()[-2]))
                    parsed_data['max_salary'] = cast(int | None, str_to_numeric(matching.groups()[-1]))
            else:
                matching = re.search(fr'{regex_patterns.salary}\Z', str_2)
                if matching:
                    parsed_data['min_salary'] = cast(int | None, str_to_numeric(matching.groups()[-1]))
                    parsed_data['max_salary'] = parsed_data['min_salary']
            # Extracting full vacancy text URL on the website from the Telegram message text
            # Извлечение URL вакансии на сайте из текста сообщения Telegram
            matching = re.search(regex_patterns.url, text_part)
            if matching:
                parsed_data['url'] = matching.group(0)
            # Extracting subscription to job vacancy messages from the Telegram message text
            # Извлечение информации о подписке рассылки из текста сообщения Telegram
            matching = re.sub(f'{"|".join(tg_vacancy_text_signs.subscription)}', '', str_last)
            if matching:
                parsed_data['subscription'] = matching.strip('\"\' *_`')
            # Подсчет успешно распарсенных полей / Counting successfully parsed fields
            parsed_fields = ['position_msg', 'location', 'experience_msg', 'min_salary', 'max_salary', 'company', 'url',
                             'subscription']
            unsuccessfully_parsed_fields = [field for field in parsed_fields if parsed_data.get(field) is None]
            if unsuccessfully_parsed_fields:
                parsed_data['text_parsing_error'] = (f'{len(unsuccessfully_parsed_fields)} | {len(parsed_fields)},'
                                                     f' {', '.join(unsuccessfully_parsed_fields)}'
                                                     f'{', separate' if text_part.find('\n\n') != -1 else ''}')
            parsed_vacancies_data.append(parsed_data)
        return parsed_vacancies_data


class TgStatisticTextParser(MessageParser):
    """
    Класс для парсинга сообщений Telegram со статистикой, возвращает словарь с результатами парсинга
    """

    @staticmethod
    def set_numeric_attr(text: str, patterns: list) -> None | int | float:
        """
        Extracting numerical values from the Telegram message text
        Извлечение числового значения из текста сообщения Telegram
        """

        result = None
        pattern = f"(?:({'|'.join(patterns)}):? +)({regex_patterns.numeric})"
        match = re.search(pattern, text)
        if match and len(match.groups()) >= 2:
            result = str_to_numeric(match.group(2))
        return result

    def parse(self, text: str) -> dict:
        """
        Функция парсинга сообщений Telegram со статистикой, возвращает словарь с результатами парсинга
        """

        # Extracting numerical values from the Telegram message text
        # Извлечение числовых значений из текста сообщения Telegram
        if text.find('Jobs for 30 days') != -1:
            pass
        parsed_data = {'vacancies_in_30d': self.set_numeric_attr(text, tg_statistic_text_signs.vacancies_in_30d),
                       'candidates_online': self.set_numeric_attr(text, tg_statistic_text_signs.candidates_online),
                       'responses_to_vacancies': self.set_numeric_attr(text,
                                                                       tg_statistic_text_signs.responses_to_vacancies),
                       'vacancies_per_week': self.set_numeric_attr(text, tg_statistic_text_signs.vacancies_per_week),
                       'candidates_per_week': self.set_numeric_attr(text, tg_statistic_text_signs.candidates_per_week)}
        # Extracting salary information from the Telegram message text
        # Извлечение информации о зарплате из текста сообщения Telegram
        pattern = f"(?:({'|'.join(tg_statistic_text_signs.salary)}):? +){regex_patterns.salary_range}"
        match = re.search(pattern, text)
        if match and len(match.groups()) >= 3:
            parsed_data['min_salary'] = cast(int, str_to_numeric(match.group(2)))
            parsed_data['max_salary'] = cast(int, str_to_numeric(match.group(3)))
        # Подсчет успешно распарсенных полей / Counting successfully parsed fields
        parsed_fields = ['vacancies_in_30d', 'candidates_online', 'responses_to_vacancies', 'vacancies_per_week',
                         'candidates_per_week']
        unsuccessfully_parsed_fields = [field for field in parsed_fields if parsed_data.get(field) is None]
        if unsuccessfully_parsed_fields:
            parsed_data['parsing_error'] = (f'{len(unsuccessfully_parsed_fields)} | {len(parsed_fields)},'
                                            f' {', '.join(unsuccessfully_parsed_fields)}')
        return parsed_data


class EmailRawMessageParser(MessageParser):
    """
    Класс для парсинга исходных сообщений Email, возвращает словарь с результатами парсинга
    """

    def parse(self, email_uid: int, email_body: dict) -> dict:
        """
        Функция для парсинга исходных сообщений Email, возвращает словарь с результатами парсинга
        """

        # Получаем объект сообщения электронной почты (email.message.Message или EmailMessage)
        email_message = cast(EmailMessage, message_from_bytes(email_body[b'RFC822'], policy=policy.default))
        # Парсим объект сообщения и извлекаем текст и вложения
        date = parse_date_string(email_message['Date'])
        parsed_data = {'email_uid': email_uid,
                       'message_id': None,
                       'from': decode_email_field(email_message['From']),
                       'subject': decode_email_field(email_message['Subject']),
                       'date': date.astimezone() if date else None,
                       'text': '',
                       'html': '',
                       'attachments': [],
                       'message_source_id': MessageSources.EMAIL.value}
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    parsed_data['text'] = part.get_content()
                elif content_type == 'text/html':
                    parsed_data['html'] = part.get_content()
                elif part.get_content_disposition() == 'attachment':
                    parsed_data['attachments'].append({'filename': part.get_filename(),
                                                       'content': part.get_content()})
        else:
            try:
                content = email_message.get_content()
                content_type = email_message.get_content_type()
                if content_type == 'text/html':
                    parsed_data['html'] = content
                else:
                    parsed_data['text'] = content
            except (KeyError, AttributeError, UnicodeDecodeError, LookupError) as err:
                # Ловим конкретные ошибки, которые могут возникнуть
                print(err.__class__.__name__, str(err))
                payload = email_message.get_payload(decode=True)
                if isinstance(payload, bytes):
                    parsed_data['text'] = payload.decode('utf-8', errors='ignore')
                else:
                    parsed_data['text'] = str(payload)
        # Определение типа сообщения / Determining the message type
        message_type = email_detect_message_type(parsed_data['html'])
        parsed_data['message_type_id'] = message_type.get_message_type_id(message_type)
        # Подсчет успешно распарсенных полей / Counting successfully parsed fields
        parsed_fields = ['email_uid', 'date', 'text', 'html']
        unsuccessfully_parsed_fields = [field for field in parsed_fields if parsed_data.get(field) is None]
        if unsuccessfully_parsed_fields:
            parsed_data['parsing_error'] = (f'{len(unsuccessfully_parsed_fields)} | {len(parsed_fields)},'
                                            f' {', '.join(unsuccessfully_parsed_fields)}')
        return parsed_data


if __name__ == '__main__':
    pass

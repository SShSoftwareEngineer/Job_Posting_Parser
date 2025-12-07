import base64
import binascii
import json
import re
import urllib.parse
from abc import ABC, abstractmethod
from email import message_from_bytes, policy
from email.message import EmailMessage
from typing import cast

from bs4 import BeautifulSoup
from telethon.tl.types import Message

from config_handler import tg_vacancy_text_signs, regex_patterns, tg_statistic_text_signs, tg_messages_signs, \
    email_messages_signs, email_vacancy_sel_0, email_vacancy_junk, email_vacancy_sel_1
from configs.config import MessageSources, MessageTypes, VacancyAttrs
from email_handler import decode_email_field
from utils import str_to_numeric, parse_date_string


class MessageParser(ABC):
    """
    Абстрактный класс, возвращает словарь с результатами парсинга
    """

    @abstractmethod
    def parse(self, **options) -> dict:
        pass


class TgRawParser(MessageParser):
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


class TgVacancyParser(MessageParser):
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
        message_parts = self.vacancy_split(text)
        parsed_vacancies_data = []
        # Обработка каждой части текста сообщения
        for message_part in message_parts:
            parsed_data = {}
            message_part = message_part.replace('\n\n', '\n').strip()
            # Извлечение строк с необходимой информацией / Extracting lines with the necessary information
            strings = message_part.split('\n')
            str_1 = re.sub(r'[*_`]+', '', strings[0]).replace('  ', ' ')
            str_2 = re.sub(r'[*_`]+', '', strings[1]).replace('  ', ' ')
            str_last = re.sub(r'[*_`]+', '', strings[-1]).replace('  ', ' ')
            # Extracting the vacancy description /Извлечение описания вакансии
            parsed_data[VacancyAttrs.JOB_DESC.attr_id] = '\n'.join(strings[2:-2] if len(strings) > 4 else [])
            # Extracting the position and company name / Извлечение позиции, названия компании
            matching = re.split(f"{'|'.join(tg_vacancy_text_signs.position_company)}", str_1)
            if matching:
                parsed_data[VacancyAttrs.POSITION.attr_id] = matching[0]
                if len(matching) > 1:
                    parsed_data[VacancyAttrs.COMPANY.attr_id] = matching[1]
            else:
                parsed_data[VacancyAttrs.POSITION.attr_id] = str_1
            # Extracting the company location and experience requirements / Извлечение локации компании, опыта работы
            matching = re.search(
                f'(.+), {regex_patterns.numeric}? ?({"|".join(tg_vacancy_text_signs.location_experience)})', str_2)
            if matching:
                parsed_data[VacancyAttrs.LOCATION.attr_id] = matching.group(1)
                parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = cast(int | None, str_to_numeric(matching.group(2)))
                if matching.group(2) is None and matching.group(3) is not None:
                    parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = 0
            # Extracting salary information / Извлечение информации о зарплате
            salary_min, salary_max = get_salary(str_2)
            if salary_min:
                parsed_data[VacancyAttrs.SALARY_FROM.attr_id] = salary_min
            if salary_max:
                parsed_data[VacancyAttrs.SALARY_TO.attr_id] = salary_max
            # Extracting full vacancy text URL on the website / Извлечение URL вакансии на сайте
            matching = re.search(regex_patterns.url, message_part)
            if matching:
                parsed_data[VacancyAttrs.URL.attr_id] = matching.group(0)
            # Extracting subscription to job vacancy messages / Извлечение информации о подписке рассылки
            matching = re.sub(f'{"|".join(tg_vacancy_text_signs.subscription)}', '', str_last)
            if matching:
                parsed_data[VacancyAttrs.SUBSCRIPTION.attr_id] = matching.strip('\"\' *_`')
            # Сортировка данных парсинга
            parsed_data = dict(sorted(parsed_data.items()))
            # Подсчет успешно распарсенных полей / Counting successfully parsed fields
            parsed_data['text_parsing_error'] = ''
            parsed_fields = [VacancyAttrs.POSITION.attr_id, VacancyAttrs.JOB_DESC.attr_id,
                             VacancyAttrs.LOCATION.attr_id, VacancyAttrs.EXPERIENCE.attr_id,
                             VacancyAttrs.SALARY_FROM.attr_id, VacancyAttrs.SALARY_TO.attr_id,
                             VacancyAttrs.COMPANY.attr_id, VacancyAttrs.URL.attr_id, VacancyAttrs.SUBSCRIPTION.attr_id]
            if message_part.find('$') == -1:
                parsed_fields.remove(VacancyAttrs.SALARY_FROM.attr_id)
                parsed_fields.remove(VacancyAttrs.SALARY_TO.attr_id)
            unsuccessfully_parsed_fields = [field for field in parsed_fields if parsed_data.get(field) is None]
            if unsuccessfully_parsed_fields:
                unsuccessfully_parsed_fields = [VacancyAttrs.get_name_by_id(attr_id) for attr_id in
                                                unsuccessfully_parsed_fields.copy()]
                parsed_data['text_parsing_error'] = (f'{len(unsuccessfully_parsed_fields)} | {len(parsed_fields)},'
                                                     f' {', '.join(unsuccessfully_parsed_fields)}'
                                                     f'{', separate' if message_part.find('\n\n') != -1 else ''}')
            parsed_vacancies_data.append(parsed_data)
        return parsed_vacancies_data


class TgStatisticParser(MessageParser):
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

        # Extracting numerical values / Извлечение числовых значений
        if text.find('Jobs for 30 days') != -1:
            pass
        parsed_data = {'vacancies_in_30d': self.set_numeric_attr(text, tg_statistic_text_signs.vacancies_in_30d),
                       'candidates_online': self.set_numeric_attr(text, tg_statistic_text_signs.candidates_online),
                       'responses_to_vacancies': self.set_numeric_attr(text,
                                                                       tg_statistic_text_signs.responses_to_vacancies),
                       'vacancies_per_week': self.set_numeric_attr(text, tg_statistic_text_signs.vacancies_per_week),
                       'candidates_per_week': self.set_numeric_attr(text, tg_statistic_text_signs.candidates_per_week)}
        # Extracting salary information / Извлечение информации о зарплате
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


class EmailRawParser(MessageParser):
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
                # Обрабатываем конкретные ошибки, которые могут возникнуть
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


class EmailVacancyParserVer0(MessageParser):
    """
    Класс для парсинга HTML содержимого сообщений Email с вакансиями, возвращает словарь с результатами парсинга
    Формат сообщений до 2025-01-24 включительно
    """

    def parse(self, html: str) -> list[dict]:
        """
        Функция для парсинга HTML содержимого сообщений Email с вакансиями, возвращает словарь с результатами парсинга
        """

        # Create a BeautifulSoup object for parsing the HTML page with the job posting text
        # Создаем объект BeautifulSoup для парсинга HTML-страницы с текстом вакансии
        soup = BeautifulSoup(html, 'lxml')
        # Разделение HTML сообщения с несколькими вакансиями на отдельные части по заданному тегу и стилю
        message_parts = None
        for splitter in email_vacancy_sel_0.splitter_selectors:
            if message_parts is None:
                message_parts = soup.find_all(splitter.tag, style=get_style_checker(splitter.attr_value))
        parsed_vacancies_data = []
        # Обработка каждой части HTML сообщения с вакансией
        for message_part in message_parts:
            parsed_data = {}
            # Извлечение позиции и URL, название позиции находится в первом теге <a>
            sel = email_vacancy_sel_0.position_url_selector
            position_url_tag = message_part.find(sel.tag, style=get_style_checker(sel.attr_value))
            if position_url_tag:
                parsed_data[VacancyAttrs.POSITION.attr_id] = position_url_tag.get_text(strip=True)
                # URL находится в атрибуте href
                parsed_data[VacancyAttrs.URL.attr_id] = get_real_url(position_url_tag.get('href'))
            # Извлечение названия компании по заданному селектору
            sel = email_vacancy_sel_0.company_selector
            company_tag = message_part.find(sel.tag, class_=get_class_checker(sel.attr_value))
            company_text = company_tag.get_text(strip=True) if company_tag else ''
            if company_text:
                parsed_data[VacancyAttrs.COMPANY.attr_id] = junk_removal(company_text, email_vacancy_junk.company)
            # Извлечение локации компании, опыта работы, информации о зарплате,
            # которые содержатся в теге <p> с классом djinni-whois-expanded.
            sel = email_vacancy_sel_0.location_experience_salary_selector
            location_experience_salary_tag = message_part.find(sel.tag, class_=get_class_checker(sel.attr_value))
            tag_text = location_experience_salary_tag.get_text(strip=True) if location_experience_salary_tag else ''
            if tag_text:
                # Извлечение информации о зарплате, которая содержится в отдельном теге <span> внутри тега <p>
                sel = email_vacancy_sel_0.salary_selector
                salary_tag = location_experience_salary_tag.find(sel.tag, style=get_style_checker(sel.attr_value))
                salary_text = salary_tag.get_text(strip=True) if salary_tag else ''
                if salary_text:
                    salary_min, salary_max = get_salary(salary_text)
                    if salary_min:
                        parsed_data[VacancyAttrs.SALARY_FROM.attr_id] = salary_min
                    if salary_max:
                        parsed_data[VacancyAttrs.SALARY_TO.attr_id] = salary_max
                # Удаляем зарплату из общего текста, чтобы получить чистую Локацию/Опыт
                tag_text = tag_text.replace(salary_text, '').strip()
                # Extracting a company location and experience requirements / Извлечение локации компании, опыта работы
                parts = [part.strip() for part in tag_text.split('·') if part.strip()]
                experience_text = None
                if len(parts) >= 1:
                    experience_text = parts[0]
                if len(parts) >= 2:
                    parsed_data[VacancyAttrs.LOCATION.attr_id] = parts[0]
                    experience_text = parts[1]
                parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = junk_removal(experience_text,
                                                                            email_vacancy_junk.experience)
            # Извлекаем описание вакансии, которое содержится в первом теге <p> после таблицы с основными данными
            sel = email_vacancy_sel_0.job_desc_selector
            job_desc_tag = message_part.find(sel.tag, style=get_style_checker(sel.attr_value))
            if job_desc_tag:
                job_desc_text = job_desc_tag.get_text(strip=True) if job_desc_tag else ''
                parsed_data[VacancyAttrs.JOB_DESC.attr_id] = junk_removal(job_desc_text,
                                                                          email_vacancy_junk.job_desc)
            parsed_vacancies_data.append(parsed_data)
        return parsed_vacancies_data


class EmailVacancyParserVer1(MessageParser):
    """
    Класс для парсинга HTML содержимого сообщений Email с вакансиями, возвращает словарь с результатами парсинга
    Формат сообщений после 2025-01-24
    """

    def parse(self, html: str) -> list[dict]:
        """
        Функция для парсинга HTML содержимого сообщений Email с вакансиями, возвращает словарь с результатами парсинга
        Формат сообщений после 2025-01-24
        """

        # Create a BeautifulSoup object for parsing the HTML page with the job posting text
        # Создаем объект BeautifulSoup для парсинга HTML-страницы с текстом вакансии
        soup = BeautifulSoup(html, 'lxml')
        # Разделение HTML сообщения с несколькими вакансиями на отдельные части по заданному тегу и стилю
        splitter = email_vacancy_sel_1.splitter_selector
        message_parts = soup.find_all(splitter.tag, class_=get_class_checker(splitter.attr_value))
        parsed_vacancies_data = []
        # Обработка каждой части HTML сообщения с вакансией
        for message_part in message_parts:
            parsed_data = {}
            # Извлечение позиции и URL
            position_url_tag = message_part.select_one(email_vacancy_sel_1.position_url_selector)
            if position_url_tag:
                parsed_data[VacancyAttrs.POSITION.attr_id] = position_url_tag.get_text(strip=True)
                # URL находится в атрибуте href
                parsed_data[VacancyAttrs.URL.attr_id] = get_real_url(position_url_tag.get('href'))
            # Извлечение информации о зарплате
            salary_tag = message_part.select_one(email_vacancy_sel_1.salary_selector)
            if salary_tag:
                salary_text = salary_tag.get_text(strip=True)
                salary_min, salary_max = get_salary(salary_text)
                if salary_min:
                    parsed_data[VacancyAttrs.SALARY_FROM.attr_id] = salary_min
                if salary_max:
                    parsed_data[VacancyAttrs.SALARY_TO.attr_id] = salary_max
            # Извлечение названия компании по заданному селектору
            sel = email_vacancy_sel_1.company_div_selector
            company_div_tag = message_part.find(sel.tag, style=get_style_checker(sel.attr_value))
            if company_div_tag:
                sel = email_vacancy_sel_1.company_span_selector
                company_span_tag = company_div_tag.find(sel.tag, class_=get_style_checker(sel.attr_value))
                if company_span_tag:
                    parsed_data[VacancyAttrs.COMPANY.attr_id] = company_span_tag.get_text(strip=True)
            # Получение деталей вакансии (опыт, английский, формат работы, локация)
            sel = email_vacancy_sel_1.experience_lingvo_worktype_location_selector
            details_tag = message_part.find(sel.tag, class_=sel.attr_value)
            if details_tag:
                parts = [part.strip() for part in details_tag.get_text().split('·') if part.strip()]
                if parts[0]:
                    # Extracting the experience requirements / Извлечение опыта работы
                    matching = re.search(
                        f'{regex_patterns.numeric}? ?({"|".join(email_vacancy_junk.experience)})', parts[0])
                    if matching:
                        parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = cast(int | None,
                                                                            str_to_numeric(matching.group(1)))
                        if matching.group(1) is None and matching.group(2) is not None:
                            parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = 0
                if parts[1]:
                    # Extracting the lingvo level / Извлечение уровня знания языка
                    parsed_data[VacancyAttrs.LINGVO.attr_id] = junk_removal(parts[1], email_vacancy_junk.lingvo)
                if parts[2]:
                    # Extracting work format / Извлечение типа работы
                    parsed_data[VacancyAttrs.WORK_TYPE.attr_id] = parts[2]
                if parts[3]:
                    # Extracting candidate locations / Извлечение локации соискателей
                    parsed_data[VacancyAttrs.CANDIDATE_LOCATIONS.attr_id] = parts[3]
            # Извлекаем описание вакансии
            sel = email_vacancy_sel_1.job_desc_selector
            job_desc_tag = message_part.find(sel.tag, style=get_style_checker(sel.attr_value))
            if job_desc_tag:
                job_desc_text = job_desc_tag.get_text(strip=True) if job_desc_tag else ''
                if job_desc_text:
                    parsed_data[VacancyAttrs.JOB_DESC.attr_id] = junk_removal(job_desc_text,
                                                                              email_vacancy_junk.job_desc)
            # Извлекаем параметры подписки
            sel = email_vacancy_sel_1.subscription_selector
            subscription_tag = message_part.find(sel.tag, class_=get_class_checker(sel.attr_value))
            if subscription_tag:
                subscription_text = subscription_tag.get_text(strip=True)
                parsed_data[VacancyAttrs.SUBSCRIPTION.attr_id] = junk_removal(subscription_text,
                                                                              email_vacancy_junk.subscription)
            parsed_vacancies_data.append(parsed_data)
        return parsed_vacancies_data


def tg_detect_message_type(msg_text: str) -> MessageTypes:
    """
    Определяет тип сообщения Telegram по его тексту
    """
    result = MessageTypes.TG_UNKNOWN
    for config_type_name in tg_messages_signs.model_fields.keys():
        matching = re.search(f"{'|'.join(getattr(tg_messages_signs, config_type_name))}", msg_text)
        if matching:
            result = MessageTypes.get_message_type_by_config_name(config_type_name)
    if all([result == MessageTypes.TG_UNKNOWN, len(msg_text) < 10, msg_text.find(' ') == -1]):
        result = MessageTypes.TG_SERVICE
    return result


def email_detect_message_type(email_html: str) -> MessageTypes:
    """
    Определяет тип Email сообщения по его HTML или тексту
    """

    result = MessageTypes.EMAIL_UNKNOWN
    soup = BeautifulSoup(email_html, 'lxml')
    for vacancy_signs in email_messages_signs.vacancy:
        if soup.find_all(vacancy_signs.tag, style=get_style_checker(vacancy_signs.attr_value)):
            result = MessageTypes.EMAIL_VACANCY
    return result


def junk_removal(text: str, junk_list: list[str]) -> str:
    """
    Удаление служебных символов и ненужные фрагментов из текста
    """
    for junk in junk_list:
        text = text.replace(junk, '')
    return text.strip()


def get_salary(salary_str: str) -> tuple[int | None, int | None]:
    """
    Извлекает информацию о заработной плате по шаблону
    """
    salary_from = salary_to = None
    matching = re.search(fr'{regex_patterns.salary_range}\Z', salary_str)
    if matching:
        if len(matching.groups()) == 2:
            salary_from = cast(int | None, str_to_numeric(matching.groups()[-2]))
            salary_to = cast(int | None, str_to_numeric(matching.groups()[-1]))
    else:
        matching = re.search(fr'{regex_patterns.salary}\Z', salary_str)
        if matching:
            salary_from = cast(int | None, str_to_numeric(matching.groups()[-1]))
            salary_to = salary_from
    return salary_from, salary_to


def get_real_url(mandrillapp_url: str) -> str | None:
    """
    Извлекает реальный URL из трекинговой ссылки Mandrillapp
    Args:
        mandrillapp_url: Полная ссылка вида https://mandrillapp.com/track/click/...?p=...
    Returns:
        Реальный URL или None, если не удалось извлечь
    """
    result = mandrillapp_url
    try:
        # Извлекаем параметр p из URL
        parsed = urllib.parse.urlparse(mandrillapp_url)
        params = urllib.parse.parse_qs(parsed.query)
        if 'p' in params:
            # Получаем значение параметра p
            base64_data = params['p'][0]
            # Корректируем padding для base64. Base64 строка должна быть кратна 4
            missing_padding = len(base64_data) % 4
            if missing_padding:
                base64_data += '=' * (4 - missing_padding)
            # Декодируем base64. Пробуем оба варианта декодирования
            try:
                decoded_bytes = base64.urlsafe_b64decode(base64_data)
            except Exception:
                decoded_bytes = base64.b64decode(base64_data)
            decoded_str = decoded_bytes.decode('utf-8')
            # Парсим JSON и извлекаем вложенный JSON из поля 'p'
            json_data = json.loads(decoded_str)
            inner_json_str = json_data.get('p', '')
            if inner_json_str:
                # Извлекаем реальный URL, декодируем экранированные слэши, убираем параметры отслеживания
                inner_json = json.loads(inner_json_str)
                result = inner_json.get('url', '').replace('\\/', '/').split('/?', 1)[0]
    except (ValueError, KeyError, json.JSONDecodeError, binascii.Error) as e:
        print(f'Unable to retrieve URL from {mandrillapp_url[:100]}...: {e}')
    return result


def get_style_checker(required_styles: list[str]):
    """
    Создает функцию для проверки наличия заданных стилей в строке стиля в теге
    """

    def checker(value: str):
        if not value:
            return False
        # Разбиваем значения в строке стиля на отдельные стили
        styles = [stl.strip().lower() for stl in value.split(';') if stl.strip()]
        # Проверяем, что все заданные стили есть
        return all(req_stl in styles for req_stl in required_styles)

    return checker


def get_class_checker(required_classes):
    """
    Создает функцию для проверки наличия заданных классов в строке названий классов в теге
    """

    def checker(value):
        if not value:
            return False
        # class_ в BS приходит как список
        if isinstance(value, list):
            classes = [clss.lower() for clss in value]
        else:
            classes = [clss.lower() for clss in value.split()]
        # Проверяем, что все заданные классы есть
        return all(req_clss.lower() in classes for req_clss in required_classes)

    return checker


if __name__ == '__main__':
    pass

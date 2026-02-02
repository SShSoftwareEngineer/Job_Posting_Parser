"""
Module for parsing Telegram and Email messages, as well as job postings from websites.
Модуль для парсинга сообщений Telegram и Email, а также объявлений о вакансиях с веб-сайтов.
"""

import base64
import binascii
import json
import re
import urllib.parse
from abc import ABC, abstractmethod
from collections import ChainMap
from email import message_from_bytes, policy
from bs4 import BeautifulSoup
from config_handler import config, Repls
from configs.config import MessageSources, MessageTypes, VacancyAttrs
from email_handler import decode_email_field
from utils import str_to_numeric, parse_date_string, html_to_text


class MessageParser(ABC): # pylint: disable=too-few-public-methods
    """
    Абстрактный класс, возвращает словарь с результатами парсинга
    """

    @abstractmethod
    def parse(self, **options) -> dict:
        pass


class TgRawParser(MessageParser): # pylint: disable=too-few-public-methods
    """
    Класс для парсинга исходных сообщений Telegram, возвращает словарь с результатами парсинга
    """

    def parse(self, **options) -> dict:
        """
        Функция для парсинга исходных сообщений Telegram, возвращает словарь с результатами парсинга
        """

        message = options.get('message',None) # type(message) == Message
        if message is None:
            return {}
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
            parsed_data['raw_parsing_error'] = (f'{len(unsuccessfully_parsed_fields)} | {len(parsed_fields)},'
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
        pattern = fr'((?:{"|".join(config.tg_vacancy_text_signs.splitter_pattern)}).*?)(Possible_Vacancy_Splitter)'
        text = re.sub(pattern, r'\1\n\n', text)
        text = text.replace('Possible_Vacancy_Splitter', '\n')
        return text.split('\n\n')

    def parse(self, **options) -> list[dict]: # pylint: disable=too-many-locals
        """
        Функция для парсинга списка сообщений Telegram с вакансиями, возвращает список словарей с результатами парсинга
        """

        parsed_vacancies_data = []
        text = options.get('text',None) # type(text) == str
        if not text:
            return parsed_vacancies_data
        # Разделение текста сообщения Telegram с несколькими вакансиями на отдельные части по двойным переносам строк
        message_parts = self.vacancy_split(text)
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
            parsed_data[VacancyAttrs.JOB_DESC_PREV.attr_id] = '\n'.join(strings[2:-2] if len(strings) > 4 else [])
            # Extracting the position and company name / Извлечение позиции, названия компании
            matching = re.split(f"{'|'.join(config.tg_vacancy_text_signs.position_company)}", str_1)
            if matching:
                parsed_data[VacancyAttrs.POSITION.attr_id] = matching[0]
                if len(matching) > 1:
                    parsed_data[VacancyAttrs.COMPANY.attr_id] = matching[1]
            else:
                parsed_data[VacancyAttrs.POSITION.attr_id] = str_1
            # Extracting the company location and experience requirements / Извлечение локации компании, опыта работы
            location_experience_signs = config.tg_vacancy_text_signs.location_experience
            matching = re.search(
                f'(.+), {config.regex_patterns.numeric}? ?({"|".join(location_experience_signs)})', str_2)
            if matching:
                parsed_data[VacancyAttrs.LOCATION.attr_id] = matching.group(1)
                parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = str_to_numeric(matching.group(2))
                if matching.group(2) is None and matching.group(3) is not None:
                    parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = 0
            # Extracting salary information / Извлечение информации о зарплате
            salary_min, salary_max = get_salary(str_2)
            if salary_min:
                parsed_data[VacancyAttrs.SALARY_FROM.attr_id] = salary_min
            if salary_max:
                parsed_data[VacancyAttrs.SALARY_TO.attr_id] = salary_max
            # Extracting full vacancy text URL on the website / Извлечение URL вакансии на сайте
            matching = re.search(config.regex_patterns.url, message_part)
            if matching:
                parsed_data[VacancyAttrs.URL.attr_id] = matching.group(0)
            # Extracting subscription to job vacancy messages / Извлечение информации о подписке рассылки
            matching = re.sub(f'{"|".join(config.tg_vacancy_text_signs.subscription)}', '', str_last)
            if matching:
                parsed_data[VacancyAttrs.SUBSCRIPTION.attr_id] = matching.strip('\"\' *_`')
            # Подсчет успешно распарсенных полей / Counting successfully parsed fields
            parsed_field_ids = [VacancyAttrs.POSITION.attr_id, VacancyAttrs.JOB_DESC_PREV.attr_id,
                                VacancyAttrs.LOCATION.attr_id, VacancyAttrs.EXPERIENCE.attr_id,
                                VacancyAttrs.SALARY_FROM.attr_id, VacancyAttrs.SALARY_TO.attr_id,
                                VacancyAttrs.COMPANY.attr_id, VacancyAttrs.URL.attr_id,
                                VacancyAttrs.SUBSCRIPTION.attr_id]
            parsing_error = get_parsing_error(parsed_data, parsed_field_ids, message_part)
            # Проверка на неправильное разделение вакансий / Checking for incorrect vacancy splitting
            if message_part.find('\n\n') != -1:
                parsing_error += ', separate' if parsing_error else 'separate'
            parsed_data['message_parsing_error'] = parsing_error
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
        pattern = f"(?:({'|'.join(patterns)}):? +)({config.regex_patterns.numeric})"
        match = re.search(pattern, text)
        if match and len(match.groups()) >= 2:
            result = str_to_numeric(match.group(2))
        return result

    def parse(self, **options) -> dict:
        """
        Функция парсинга сообщений Telegram со статистикой, возвращает словарь с результатами парсинга
        """

        text = options.get('text', None) # type(text) == str
        if not text:
            return {}
        # Extracting numerical values / Извлечение числовых значений
        signs = config.tg_statistic_text_signs
        parsed_data = {'vacancies_in_30d': self.set_numeric_attr(text, signs.vacancies_in_30d),
                       'candidates_online': self.set_numeric_attr(text, signs.candidates_online),
                       'responses_to_vacancies': self.set_numeric_attr(text, signs.responses_to_vacancies),
                       'vacancies_per_week': self.set_numeric_attr(text, signs.vacancies_per_week),
                       'candidates_per_week': self.set_numeric_attr(text, signs.candidates_per_week)}
        # Extracting salary information / Извлечение информации о зарплате
        pattern = f"(?:({'|'.join(config.tg_statistic_text_signs.salary)}):? +){config.regex_patterns.salary_range}"
        match = re.search(pattern, text)
        if match and len(match.groups()) >= 3:
            parsed_data['min_salary'] = str_to_numeric(match.group(2))
            parsed_data['max_salary'] = str_to_numeric(match.group(3))
        # Подсчет успешно распарсенных полей / Counting successfully parsed fields
        parsed_fields = ['vacancies_in_30d', 'candidates_online', 'responses_to_vacancies', 'vacancies_per_week',
                         'candidates_per_week']
        unsuccessfully_parsed_fields = [field for field in parsed_fields if parsed_data.get(field) is None]
        if unsuccessfully_parsed_fields:
            parsed_data['stat_parsing_error'] = (f'{len(unsuccessfully_parsed_fields)} | {len(parsed_fields)},'
                                                 f' {', '.join(unsuccessfully_parsed_fields)}')
        return parsed_data


class EmailRawParser(MessageParser): # pylint: disable=too-few-public-methods
    """
    Класс для парсинга исходных сообщений Email, возвращает словарь с результатами парсинга
    """

    def parse(self, **options) -> dict: # pylint: disable=too-many-branches
        """
        Функция для парсинга исходных сообщений Email, возвращает словарь с результатами парсинга
        """

        email_uid = options.get('email_uid', None) # type(email_uid) == int
        email_body = options.get('email_body', None) # type(email_body) == dict
        if not all([email_uid, email_body]):
            return {}
        # Получаем объект сообщения электронной почты (email.message.Message или EmailMessage)
        email_message = message_from_bytes(email_body[b'RFC822'], policy=policy.default)
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
            parsed_data['raw_parsing_error'] = (f'{len(unsuccessfully_parsed_fields)} | {len(parsed_fields)},'
                                                f' {', '.join(unsuccessfully_parsed_fields)}')
        return parsed_data


class EmailVacancyParserVer0(MessageParser): # pylint: disable=too-few-public-methods
    """
    Класс для парсинга HTML содержимого сообщений Email с вакансиями, возвращает словарь с результатами парсинга
    Формат сообщений до 2025-01-24 включительно
    """

    def parse(self, **options) -> list[dict]: # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Функция для парсинга HTML содержимого сообщений Email с вакансиями, возвращает словарь с результатами парсинга
        """

        parsed_vacancies_data = []
        html = options.get('html', None)  # type(html) == str
        if not html:
            return parsed_vacancies_data
        # Create a BeautifulSoup object for parsing the HTML page with the job posting text
        # Создаем объект BeautifulSoup для парсинга HTML-страницы с текстом вакансии
        soup = BeautifulSoup(html, 'lxml')
        # Разделение HTML сообщения с несколькими вакансиями на отдельные части по заданному тегу и стилю
        sels = config.email_vacancy_sel_0
        message_parts = None
        for splitter in sels.splitter_selectors:
            if message_parts is None:
                message_parts = soup.find_all(splitter.tag, **attr_checker(splitter.attr_name, splitter.attr_value))
        # Обработка каждой части HTML сообщения с вакансией
        for message_part in message_parts:
            parsed_data = {}
            # Извлечение позиции и URL
            sel = sels.position_url_selector
            position_url_tag = message_part.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
            if position_url_tag:
                parsed_data[VacancyAttrs.POSITION.attr_id] = position_url_tag.get_text(strip=True)
                # URL находится в атрибуте href
                parsed_data[VacancyAttrs.URL.attr_id] = get_real_url(position_url_tag.get('href'))
            # Извлечение названия компании
            sel = sels.company_selector
            company_tag = message_part.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
            company_text = company_tag.get_text(strip=True) if company_tag else ''
            if company_text:
                parsed_data[VacancyAttrs.COMPANY.attr_id] = remove_repl(company_text,
                                                                        config.email_vacancy_repls.pos_comp)
            # Извлечение локации компании, опыта работы, информации о зарплате
            sel = sels.location_experience_salary_selector
            location_experience_salary_tag = message_part.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
            tag_text = location_experience_salary_tag.get_text(strip=True) if location_experience_salary_tag else ''
            salary_text = ''
            if tag_text:
                # Извлечение информации о зарплате
                sel = sels.salary_selector
                salary_tag = location_experience_salary_tag.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
                if salary_tag:
                    salary_text = salary_tag.get_text(strip=True)
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
                    experience_text = parts[1]
                    parsed_data[VacancyAttrs.LOCATION.attr_id] = parts[0]
                if 'Український продукт' in experience_text:
                    experience_text = parts[0]
                    del parsed_data[VacancyAttrs.LOCATION.attr_id]
                if experience := str_to_numeric(remove_repl(experience_text, config.web_vacancy_repls.experience)):
                    parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = experience
            # Извлекаем описание вакансии, которое содержится в первом теге <p> после таблицы с основными данными
            sel = sels.job_desc_prev_selector
            job_desc_prev_tag = message_part.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
            if job_desc_prev_tag:
                job_desc_prev_text = job_desc_prev_tag.get_text(strip=True) if job_desc_prev_tag else ''
                parsed_data[VacancyAttrs.JOB_DESC_PREV.attr_id] = remove_repl(job_desc_prev_text,
                                                                              config.email_vacancy_repls.job_desc_prev)
            # Подсчет успешно распарсенных полей / Counting successfully parsed fields
            parsed_field_ids = [VacancyAttrs.POSITION.attr_id, VacancyAttrs.URL.attr_id,
                                VacancyAttrs.COMPANY.attr_id, VacancyAttrs.SALARY_FROM.attr_id,
                                VacancyAttrs.SALARY_TO.attr_id,
                                VacancyAttrs.EXPERIENCE.attr_id, VacancyAttrs.JOB_DESC_PREV.attr_id]
            parsed_data['message_parsing_error'] = get_parsing_error(parsed_data, parsed_field_ids, salary_text)
            parsed_vacancies_data.append(parsed_data)
        return parsed_vacancies_data


class EmailVacancyParserVer1(MessageParser): # pylint: disable=too-few-public-methods
    """
    Класс для парсинга HTML содержимого сообщений Email с вакансиями, возвращает словарь с результатами парсинга
    Формат сообщений после 2025-01-24
    """

    def parse(self, **options) -> list[dict]: # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Функция для парсинга HTML содержимого сообщений Email с вакансиями, возвращает словарь с результатами парсинга
        Формат сообщений после 2025-01-24
        """

        parsed_vacancies_data = []
        html = options.get('html', None)  # type(html) == str
        if not html:
            return parsed_vacancies_data
        # Create a BeautifulSoup object for parsing the HTML page with the job posting text
        # Создаем объект BeautifulSoup для парсинга HTML-страницы с текстом вакансии
        soup = BeautifulSoup(html, 'lxml')
        sels = config.email_vacancy_sel_1
        repls = config.web_vacancy_repls
        # Разделение HTML сообщения с несколькими вакансиями на отдельные части по заданному тегу и стилю
        splitter = sels.splitter_selector
        message_parts = soup.find_all(splitter.tag, **attr_checker(splitter.attr_name, splitter.attr_value))
        # Обработка каждой части HTML сообщения с вакансией
        for message_part in message_parts:
            parsed_data = {}
            # Извлечение позиции и URL
            position_url_tag = message_part.select_one(sels.position_url_selector)
            if position_url_tag:
                parsed_data[VacancyAttrs.POSITION.attr_id] = position_url_tag.get_text(strip=True)
                # URL находится в атрибуте href
                parsed_data[VacancyAttrs.URL.attr_id] = get_real_url(position_url_tag.get('href'))
            # Извлечение информации о зарплате
            salary_tag = message_part.select_one(sels.salary_selector)
            salary_text = ''
            if salary_tag:
                salary_text = salary_tag.get_text(strip=True)
                salary_min, salary_max = get_salary(salary_text)
                if salary_min:
                    parsed_data[VacancyAttrs.SALARY_FROM.attr_id] = salary_min
                if salary_max:
                    parsed_data[VacancyAttrs.SALARY_TO.attr_id] = salary_max
            # Извлечение названия компании по заданному селектору
            sel = sels.company_div_selector
            company_div_tag = message_part.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
            if company_div_tag:
                sel = sels.company_span_selector
                company_span_tag = company_div_tag.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
                if company_span_tag:
                    parsed_data[VacancyAttrs.COMPANY.attr_id] = company_span_tag.get_text(strip=True)
            # Получение деталей вакансии (опыт, английский, формат работы, локация)
            sel = sels.experience_lingvo_worktype_location_selector
            details_tag = message_part.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
            if details_tag:
                parts = [part.strip() for part in details_tag.get_text().split('·')]
                if parts[0]:
                    # Extracting the experience requirements / Извлечение опыта работы
                    matching = re.search(
                        f'{config.regex_patterns.numeric}? ?({"|".join(repls.experience.remove)})', parts[0])
                    if matching:
                        parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = (
                            str_to_numeric(remove_repl(matching.group(1), repls.experience)))
                        if matching.group(1) is None and matching.group(2) is not None:
                            parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = 0
                if parts[1]:
                    # Extracting the lingvo level / Извлечение уровня знания языка
                    parsed_data[VacancyAttrs.LINGVO.attr_id] = remove_repl(parts[1], repls.lingvo)
                if parts[2]:
                    # Extracting work format / Извлечение формата работы
                    parsed_data[VacancyAttrs.EMPLOYMENT.attr_id] = remove_repl(parts[2], repls.employment)
                if parts[3]:
                    # Extracting candidate locations / Извлечение локации соискателей
                    parsed_data[VacancyAttrs.CANDIDATE_LOCATIONS.attr_id] = remove_repl(parts[3],
                                                                                        repls.candidate_locations)
            # Извлекаем описание вакансии
            sel = sels.job_desc_prev_selector
            job_desc_prev_tag = message_part.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
            if job_desc_prev_tag:
                job_desc_prev_text = job_desc_prev_tag.get_text(strip=True) if job_desc_prev_tag else ''
                if job_desc_prev_text:
                    parsed_data[VacancyAttrs.JOB_DESC_PREV.attr_id] = (
                        remove_repl(job_desc_prev_text, config.email_vacancy_repls.job_desc_prev))
            # Извлекаем параметры подписки
            sel = sels.subscription_selector
            subscription_tag = message_part.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
            if subscription_tag:
                subscription_text = subscription_tag.get_text(strip=True)
                parsed_data[VacancyAttrs.SUBSCRIPTION.attr_id] = remove_repl(subscription_text,
                                                                             config.email_vacancy_repls.subscription)
            # Подсчет успешно распарсенных полей / Counting successfully parsed fields
            parsed_field_ids = [VacancyAttrs.POSITION.attr_id, VacancyAttrs.URL.attr_id,
                                VacancyAttrs.SALARY_FROM.attr_id, VacancyAttrs.SALARY_TO.attr_id,
                                VacancyAttrs.EXPERIENCE.attr_id, VacancyAttrs.EMPLOYMENT.attr_id,
                                VacancyAttrs.CANDIDATE_LOCATIONS.attr_id, VacancyAttrs.JOB_DESC_PREV.attr_id,
                                VacancyAttrs.SUBSCRIPTION.attr_id]
            parsed_data['message_parsing_error'] = get_parsing_error(parsed_data, parsed_field_ids, salary_text)
            parsed_vacancies_data.append(parsed_data)
        return parsed_vacancies_data


class WebVacancyParser(MessageParser): # pylint: disable=too-few-public-methods
    """
    Класс для парсинга объявления о вакансии с сайта, возвращает словарь с результатами парсинга
    """

    def parse(self, **options) -> dict: # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Класс для парсинга объявления о вакансии с сайта, возвращает словарь с результатами парсинга
        """

        def table_parsing(two_col_table) -> dict:
            """
            Парсинг таблицы с двумя колонками
            """
            result_dict = {}
            for table_row in two_col_table.find_all('tr') or []:
                table_cols = table_row.find_all('td')
                if len(table_cols) == 2:
                    result_dict.update({table_cols[0].get_text(strip=True): table_cols[1].get_text(strip=True)})
            return result_dict

        parsed_data = {}
        html = options.get('html', None)  # type(html) == str
        if not html:
            return parsed_data
        soup = BeautifulSoup(html, 'lxml')
        sels = config.web_vacancy_sel
        repls = config.web_vacancy_repls
        # Извлечение позиции
        position_tag = soup.select_one(sels.position_selector)
        if position_tag:
            nested_span = position_tag.find('span')
            if nested_span:
                nested_span.decompose()
            parsed_data[VacancyAttrs.POSITION.attr_id] = html_to_text(position_tag.get_text(strip=True))
        # Extracting company
        company_tag = soup.select_one(sels.company_selector)
        if company_tag:
            parsed_data[VacancyAttrs.COMPANY.attr_id] = html_to_text(company_tag.get_text(strip=True))
        # Extracting job description
        sel = sels.job_desc_selector
        job_desc_tag = soup.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
        if job_desc_tag:
            parsed_data[VacancyAttrs.JOB_DESC.attr_id] = html_to_text(str(job_desc_tag))
        # Extracting URL
        sel = sels.url_selector
        url_tag = soup.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
        if url_tag:
            parsed_data[VacancyAttrs.URL.attr_id] = url_tag['href'].split('-', 1)[0]
        # Инициализируем список заметок / Initializing the notes list
        notes = []
        # Extracting tech stack / Извлечение технического стека
        tech_stack = {}
        tech_stack_h2 = soup.find(lambda tag: tag.name == 'h2' and any(
            ['skills' in tag.get_text().lower(), 'досвід' in tag.get_text().lower()]))
        tech_stack_tag = tech_stack_h2.find_next('table') if tech_stack_h2 else None
        if tech_stack_tag:
            tech_stack.update(table_parsing(tech_stack_tag))
        sel = sels.more_tech_stack_selector
        more_tech_stack_div = soup.find(sel.tag, **attr_checker(sel.attr_name, sel.attr_value))
        more_tech_stack_tag = more_tech_stack_div.find_next('table') if more_tech_stack_div else None
        if more_tech_stack_tag:
            tech_stack.update(table_parsing(more_tech_stack_tag))
        second_tech_stack = soup.select(sels.second_tech_stack_selector)
        if second_tech_stack:
            second_tech_stack_list = second_tech_stack[0].get_text(strip=True).split(', ')
            second_tech_stack_dict = dict.fromkeys(second_tech_stack_list, '')
            tech_stack = second_tech_stack_dict | tech_stack  # Merge dictionaries, first dictionary has higher priority
        # Удаляем сведения о языках, случайно попавшие в технический стек
        tech_stack.pop('English', None)
        tech_stack.pop('Ukrainian', None)
        tech_stack.pop('Russian', None)
        if tech_stack:
            for tech, skill in tech_stack.items():
                if skill:
                    notes.append(remove_repl(f'{tech}: {skill}', repls.notes))
        # Filling the lingvo level / Заполнение уровня знания языка
        lingvo = {}
        lingvo_list = []
        lingvo_table = None
        lingvo_in_card = None
        lingvo_h2 = soup.find(lambda tag: tag.name == 'h2' and any(
            ['language' in tag.get_text().lower(), 'мовами' in tag.get_text().lower()]))
        lingvo_tag = lingvo_h2.find_next('table') if lingvo_h2 else None
        if lingvo_tag:
            lingvo_table = table_parsing(lingvo_tag)
            lingvo.update(lingvo_table)
        if lingvo:
            # Извлекаем отдельно уровень знания английского языка
            if lingvo.get('English'):
                lingvo_list.append(remove_repl(lingvo.pop('English'), repls.lingvo))
            if lingvo.get('Англійська'):
                lingvo_list.append(remove_repl(lingvo.pop('Англійська'), repls.lingvo))
            # Требования к остальным языкам записываем в заметки
            for language, skill in lingvo.items():
                notes.append(remove_repl(f'{language}: {skill}', repls.notes))
        # Job card processing
        employment = []
        salary_text = ''
        job_card_tag = soup.select_one(sels.job_card_selector)
        if job_card_tag:
            all_ul_tag = job_card_tag.find_all('ul', recursive=False)
            if len(all_ul_tag) == 3:
                # Блок № 1. Требования вакансии
                requirements = []
                ul_tag = all_ul_tag[0]
                all_li_tag = ul_tag.find_all('li')
                # Выбираем основную и дополнительную информацию из каждого тега в список
                for index, li_tag in enumerate(all_li_tag or []):
                    info_tag = li_tag.find('strong')
                    if info_tag:
                        info_tag_text = html_to_text(info_tag.get_text(strip=True))
                        if info_tag_text and info_tag_text not in requirements:
                            requirements.append(info_tag_text)
                    if index in [0, 3]:  # 0 - Experience, 3 - Lingvo
                        note_tag = li_tag.find('small')  # примечания отправляем в заметки
                        if note_tag:
                            notes.append(note_tag.get_text(strip=True))
                # Обрабатываем информацию о зарплате из второй строки, если она там есть и удаляем эту строку из списка
                if len(requirements) >= 2 and requirements[1].find('$') != -1:
                    # Extracting salary information / Извлечение информации о зарплате
                    salary_text = requirements[1]
                    salary_min, salary_max = get_salary(salary_text)
                    if salary_min:
                        parsed_data[VacancyAttrs.SALARY_FROM.attr_id] = salary_min
                    if salary_max:
                        parsed_data[VacancyAttrs.SALARY_TO.attr_id] = salary_max
                    del requirements[1]
                # Обрабатываем информацию из списка требований
                for index, req_str in enumerate(requirements.copy()):
                    match index:
                        case 0:  # Experience
                            experience = re.search(config.regex_patterns.numeric,
                                                   remove_repl(req_str, repls.experience))
                            if experience:
                                parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = str_to_numeric(experience[0])
                        case 1:  # Work format
                            employment.append(remove_repl(req_str, repls.employment))
                        case 2:  # Candidate locations
                            parsed_data[VacancyAttrs.CANDIDATE_LOCATIONS.attr_id] = (
                                remove_repl(req_str, repls.candidate_locations))
                        case 3:  # Lingvo
                            lingvo_in_card = remove_repl(req_str, repls.lingvo)
                            if lingvo_in_card in ChainMap(*repls.lingvo.repl).keys():
                                lingvo_list.append(lingvo_in_card)
                            else:
                                notes.append(lingvo_in_card)
                                lingvo_in_card = None
                        case _:  # Other requirements go to notes
                            notes.append(req_str)
                # Блок № 2. Требования к навыкам / Filling in the skills table from card
                ul_tag = all_ul_tag[1]
                main_tech_tag = ul_tag.select_one(sels.main_tech_selector)
                if main_tech_tag:
                    parsed_data[VacancyAttrs.MAIN_TECH.attr_id] = html_to_text(main_tech_tag.get_text(strip=True))
                tech_stack_tag = ul_tag.find('table')
                if tech_stack_tag:
                    tech_stack.update(table_parsing(tech_stack_tag))
                # Блок № 3. Характеристики компании
                ul_tag = all_ul_tag[2]
                all_li_tag = ul_tag.find_all('li')
                for index, li_tag in enumerate(all_li_tag or []):
                    match index:
                        case 0:  # Work format
                            employment.append(
                                remove_repl(html_to_text(li_tag.get_text(strip=True)), repls.employment))
                        case 1:  # Domain
                            parsed_data[VacancyAttrs.DOMAIN.attr_id] = remove_repl(
                                html_to_text(li_tag.get_text(strip=True)), repls.domain)
                        case 2:  # Company type
                            parsed_data[VacancyAttrs.COMPANY_TYPE.attr_id] = remove_repl(
                                html_to_text(li_tag.get_text(strip=True)), repls.company_type)
                        case 3:  # Company offices
                            li_tag_text = html_to_text(li_tag.get_text(strip=True))
                            for remove_sign in repls.offices.remove:
                                if li_tag_text.find(remove_sign) != -1:
                                    parsed_data[VacancyAttrs.OFFICES.attr_id] = remove_repl(li_tag_text, repls.offices)
                                    li_tag_text = ''
                            if li_tag_text:
                                notes.append(li_tag_text)
                        case _:  # Other characteristics go to notes
                            notes.append(html_to_text(li_tag.get_text(strip=True)))
        if tech_stack:
            parsed_data[VacancyAttrs.TECH_STACK.attr_id] = ', '.join(sorted(tech_stack.keys()))
        if lingvo_list:
            parsed_data[VacancyAttrs.LINGVO.attr_id] = ', '.join(sorted(set(lingvo_list)))
        if employment:
            parsed_data[VacancyAttrs.EMPLOYMENT.attr_id] = ', '.join(employment)
        if notes:
            parsed_data[VacancyAttrs.NOTES.attr_id] = '\n'.join(sorted(set(notes)))
        # Подсчет успешно распарсенных полей / Counting successfully parsed fields
        parsed_field_ids = [VacancyAttrs.POSITION.attr_id, VacancyAttrs.COMPANY.attr_id,
                            VacancyAttrs.JOB_DESC.attr_id, VacancyAttrs.URL.attr_id,
                            VacancyAttrs.SALARY_FROM.attr_id, VacancyAttrs.SALARY_TO.attr_id,
                            VacancyAttrs.EXPERIENCE.attr_id, VacancyAttrs.CANDIDATE_LOCATIONS.attr_id,
                            VacancyAttrs.LINGVO.attr_id, VacancyAttrs.EMPLOYMENT.attr_id,
                            VacancyAttrs.DOMAIN.attr_id, VacancyAttrs.COMPANY_TYPE.attr_id,
                            VacancyAttrs.MAIN_TECH.attr_id, VacancyAttrs.TECH_STACK.attr_id, ]
        if not lingvo_table and not lingvo_in_card:
            parsed_field_ids.remove(VacancyAttrs.LINGVO.attr_id)
        parsed_data['web_parsing_error'] = get_parsing_error(parsed_data, parsed_field_ids, salary_text)
        return parsed_data


def tg_detect_message_type(msg_text: str) -> MessageTypes:
    """
    Определяет тип сообщения Telegram по его тексту
    """
    result = MessageTypes.TG_UNKNOWN
    for config_type_name in config.tg_messages_signs.model_fields.keys():
        matching = re.search(f"{'|'.join(getattr(config.tg_messages_signs, config_type_name))}", msg_text)
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
    for vacancy_signs in config.email_messages_signs.vacancy:
        if soup.find_all(vacancy_signs.tag, **attr_checker(vacancy_signs.attr_name, vacancy_signs.attr_value)):
            # if soup.find_all(vacancy_signs.tag, style=get_style_checker(vacancy_signs.attr_value)):
            result = MessageTypes.EMAIL_VACANCY
    return result


def remove_repl(text: str | None, patterns: Repls) -> str | None:
    """
    Замена текста по шаблону или удаление служебных символов и ненужных фрагментов текста
    """
    if text is None or text.strip() == '':
        return None
    for repl_dict in patterns.repl:
        for key, value in repl_dict.items():
            if text in sorted(value, key=len, reverse=True):
                text = key
    for pattern in sorted(patterns.remove, key=len, reverse=True):
        text = text.replace(pattern, '')
    return text.strip()


def get_salary(salary_str: str) -> tuple[int | None, int | None]:
    """
    Извлекает информацию о заработной плате по шаблону
    """
    salary_from = salary_to = None
    matching = re.search(fr'{config.regex_patterns.salary_range}\Z', salary_str)
    if matching:
        if len(matching.groups()) == 2:
            salary_from = str_to_numeric(matching.groups()[-2])
            salary_to = str_to_numeric(matching.groups()[-1])
    else:
        matching = re.search(fr'{config.regex_patterns.salary}\Z', salary_str)
        if matching:
            salary_from = str_to_numeric(matching.groups()[-1])
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
                # result = inner_json.get('url', '').replace('\\/', '/').split('/?', 1)[0]
                result = inner_json.get('url', '').replace('\\/', '/').split('-', 1)[0]
    except (ValueError, KeyError, json.JSONDecodeError, binascii.Error) as e:
        print(f'Unable to retrieve URL from {mandrillapp_url[:100]}...: {e}')
    return result


def attr_checker(attr_name: str, required_attrs: list[str]) -> dict:
    """
    Универсальная функция для проверки наличия заданных значений style и class в атрибутах тега.
    Нечувствительна к регистру и порядку значений.
    """
    if attr_name.lower() == 'style':

        def checker(value: str):
            if not value:
                return False
            # Разбиваем значения в строке стиля на отдельные стили
            styles = [stl.strip().lower() for stl in value.split(';') if stl.strip()]
            # Проверяем, что все заданные стили есть
            return all(req_stl in styles for req_stl in required_attrs)

    elif attr_name.lower() in ('class', 'class_'):

        def checker(value):
            if not value:
                return False
            # class_ в виде списка, разбиваем значения на отдельные классы
            if isinstance(value, list):
                classes = [clss.lower() for clss in value]
            else:
                classes = [clss.lower() for clss in value.split()]
            # Проверяем, что все заданные классы есть
            return all(req_clss.lower() in classes for req_clss in required_attrs)

    else:

        def checker(value):
            if not value:
                return False
            return all(req_val in str(value) for req_val in required_attrs)

    key = 'class_' if attr_name.lower() == 'class' else attr_name
    return {key: checker}


def get_parsing_error(parsed_data: dict, parsed_field_ids: list, salary_text: str, ) -> str | None:
    """
    Подсчет успешно распарсенных полей / Counting successfully parsed fields
    """

    if salary_text.find('$') == -1:
        if VacancyAttrs.SALARY_FROM.attr_id in parsed_field_ids:
            parsed_field_ids.remove(VacancyAttrs.SALARY_FROM.attr_id)
        if VacancyAttrs.SALARY_TO.attr_id in parsed_field_ids:
            parsed_field_ids.remove(VacancyAttrs.SALARY_TO.attr_id)
    unsuccessfully_parsed_fields = [field_id for field_id in parsed_field_ids if parsed_data.get(field_id) is None]
    error_report = None
    if unsuccessfully_parsed_fields:
        unsuccessfully_parsed_fields = [VacancyAttrs.get_name_by_id(attr_id) for attr_id in
                                        unsuccessfully_parsed_fields.copy()]
        if len(unsuccessfully_parsed_fields) == 1:
            error_report = unsuccessfully_parsed_fields[0]
        else:
            error_report = (f'{len(unsuccessfully_parsed_fields)} | {len(parsed_field_ids)},'
                            f' {', '.join(unsuccessfully_parsed_fields)}')
    return error_report


if __name__ == '__main__':
    pass

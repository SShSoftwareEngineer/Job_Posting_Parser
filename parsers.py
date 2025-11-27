import re
from abc import ABC, abstractmethod
from email import message_from_bytes, policy
from email.message import EmailMessage
from typing import cast

from bs4 import BeautifulSoup
from telethon.tl.types import Message

from config_handler import tg_vacancy_text_signs, regex_patterns, tg_statistic_text_signs, tg_messages_signs, \
    email_messages_signs, email_vacancy_html_signs
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
            parsed_data = {}
            text_part = text_part.replace('\n\n', '\n').strip()
            # Извлечение строк с необходимой информацией / Extracting lines with the necessary information
            strings = text_part.split('\n')
            str_1 = re.sub(r'[*_`]+', '', strings[0]).replace('  ', ' ')
            str_2 = re.sub(r'[*_`]+', '', strings[1]).replace('  ', ' ')
            str_last = re.sub(r'[*_`]+', '', strings[-1]).replace('  ', ' ')
            # Extracting the vacancy description from the Telegram message text
            # Извлечение описания вакансии из сообщения Telegram
            parsed_data[VacancyAttrs.JOB_DESC.attr_id] = '\n'.join(strings[2:-2] if len(strings) > 4 else [])
            # Extracting the position and company name from the Telegram message text
            # Извлечение позиции, названия компании из текста сообщения Telegram
            matching = re.split(f"{'|'.join(tg_vacancy_text_signs.position_company)}", str_1)
            if matching:
                parsed_data[VacancyAttrs.POSITION.attr_id] = matching[0]
                if len(matching) > 1:
                    parsed_data[VacancyAttrs.COMPANY.attr_id] = matching[1]
            else:
                parsed_data[VacancyAttrs.POSITION.attr_id] = str_1
            # Extracting the company location and experience requirements from the Telegram message text
            # Извлечение локации компании, опыта работы из текста сообщения Telegram
            matching = re.search(
                f'(.+), {regex_patterns.numeric}? ?({"|".join(tg_vacancy_text_signs.location_experience)})', str_2)
            if matching:
                parsed_data[VacancyAttrs.LOCATION.attr_id] = matching.group(1)
                parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = cast(int | None, str_to_numeric(matching.group(2)))
                if matching.group(2) is None and matching.group(3) is not None:
                    parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = 0
            # Extracting salary information from the Telegram message text
            # Извлечение информации о зарплате из текста сообщения Telegram
            salary_min, salary_max = get_salary(str_2)
            if salary_min:
                parsed_data[VacancyAttrs.SALARY_FROM.attr_id] = salary_min
            if salary_max:
                parsed_data[VacancyAttrs.SALARY_TO.attr_id] = salary_max
            # Extracting full vacancy text URL on the website from the Telegram message text
            # Извлечение URL вакансии на сайте из текста сообщения Telegram
            matching = re.search(regex_patterns.url, text_part)
            if matching:
                parsed_data[VacancyAttrs.URL.attr_id] = matching.group(0)
            # Extracting subscription to job vacancy messages from the Telegram message text
            # Извлечение информации о подписке рассылки из текста сообщения Telegram
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
            if text_part.find('$') == -1:
                parsed_fields.remove(VacancyAttrs.SALARY_FROM.attr_id)
                parsed_fields.remove(VacancyAttrs.SALARY_TO.attr_id)
            unsuccessfully_parsed_fields = [field for field in parsed_fields if parsed_data.get(field) is None]
            if unsuccessfully_parsed_fields:
                unsuccessfully_parsed_fields = [VacancyAttrs.get_name_by_id(attr_id) for attr_id in
                                                unsuccessfully_parsed_fields.copy()]
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


class EmailVacancyHTMLParser(MessageParser):
    """
    Класс для парсинга сообщений Email с вакансиями, возвращает словарь с результатами парсинга
    """

    def parse(self, html: str) -> list[dict]:
        """
        Функция для парсинга сообщений Email с вакансиями, возвращает словарь с результатами парсинга
        """

        # Create a BeautifulSoup object for parsing the HTML page with the job posting text
        # Создаем объект BeautifulSoup для парсинга HTML-страницы с текстом вакансии
        soup = BeautifulSoup(html, 'lxml')
        # Разделение HTML сообщения с несколькими вакансиями на отдельные части по заданному тегу и стилю
        signs = email_vacancy_html_signs
        html_parts = None
        for splitter in signs.splitters:
            if html_parts is None:
                html_parts = soup.find_all(splitter.tag,
                                           attrs={splitter.attr_name: get_style_checker(splitter.attr_value)})
        parsed_vacancies_data = []
        # Обработка каждой части HTML сообщения с вакансией
        for html_part in html_parts:
            parsed_data = {}
            # Извлечение позиции и URL, название позиции находится в первом теге <a>
            signs = email_vacancy_html_signs.position_url_selector
            position_url_tag = html_part.find(signs.tag, attrs={signs.attr_name: get_style_checker(signs.attr_value)})
            if position_url_tag:
                parsed_data[VacancyAttrs.POSITION.attr_id] = position_url_tag.get_text(strip=True)
                # URL находится в атрибуте href
                parsed_data[VacancyAttrs.URL.attr_id] = position_url_tag.get('href')
            # Извлечение названия компании по заданному селектору
            signs = email_vacancy_html_signs.company_selector
            company_tag = html_part.find(signs.tag, attrs={signs.attr_name: get_class_checker(signs.attr_value)})
            # company_tag = html_part.find('span', class_='djinni-whois-expanded')
            company_text = company_tag.get_text(strip=True) if company_tag else ''
            if company_text:
                for pattern in email_vacancy_html_signs.position_company:
                    company_text.replace(pattern, '', 1)
                parsed_data[VacancyAttrs.COMPANY.attr_id] = company_text
            # Извлечение локации компании, опыта работы, информации о зарплате,
            # которые содержатся в теге <p> с классом djinni-whois-expanded.
            signs = email_vacancy_html_signs.location_experience_salary_selector
            location_experience_salary_tag = html_part.find(signs.tag, attrs={
                signs.attr_name: get_class_checker(signs.attr_value)})
            # location_experience_salary_tag = html_part.find('p', class_='djinni-whois-expanded')
            tag_text = location_experience_salary_tag.get_text(strip=True) if location_experience_salary_tag else ''
            if tag_text:
                # Извлечение информации о зарплате, которая содержится в отдельном теге <span> внутри тега <p>
                signs = email_vacancy_html_signs.salary_selector
                salary_tag = location_experience_salary_tag.find(signs.tag, attrs={
                    signs.attr_name: get_style_checker(signs.attr_value)})
                # salary_tag = location_experience_salary_tag.find('span',
                #                                                  style=lambda value: value and 'color:#4cae4c' in value)
                salary_text = salary_tag.get_text(strip=True) if salary_tag else ''
                if salary_text:
                    salary_min, salary_max = get_salary(salary_text)
                    if salary_min:
                        parsed_data[VacancyAttrs.SALARY_FROM.attr_id] = salary_min
                    if salary_max:
                        parsed_data[VacancyAttrs.SALARY_TO.attr_id] = salary_max
                # Удаляем зарплату из общего текста, чтобы получить чистую Локацию/Опыт
                tag_text = tag_text.replace(salary_text, '').strip()
                # Извлечение Локации и Опыта # Тут ошибка
                parts = [part.strip() for part in tag_text.split('·') if part.strip()]
                if len(parts) >= 1:
                    parsed_data[VacancyAttrs.LOCATION.attr_id] = parts[0]
                if len(parts) >= 2:
                    parsed_data[VacancyAttrs.EXPERIENCE.attr_id] = parts[1]
            # Извлекаем описание вакансии, которое содержится в первом теге <p> после таблицы с основными данными
            signs = email_vacancy_html_signs.job_desc_selector
            job_desc_tag = html_part.find(signs.tag, attrs={signs.attr_name: get_style_checker(signs.attr_value)})
            # job_desc_tag = html_part.find('p', style=lambda value: value and 'margin:5px 0;color:#333' in value)
            job_desc_text = job_desc_tag.get_text(strip=True) if job_desc_tag else ''
            if job_desc_text:
                # Получаем весь текст и удаляем "Подробнее" и <br> в конце
                job_desc_text = job_desc_tag.get_text(strip=True)
                # Удаляем текст ссылки "Подробнее" из описания, находим последнюю строку, которая является ссылкой "Подробнее"
                signs = email_vacancy_html_signs.details_link
                details_link_tag = job_desc_tag.find(signs.tag, attrs={signs.attr_name: get_style_checker(signs.attr_value)})
                # details_link = job_desc_tag.find('a', text='Подробнее')
                if details_link_tag:
                    # Находим и удаляем "Подробнее" и предшествующую ему часть текста
                    job_desc_text = job_desc_text.rsplit(details_link_tag.get_text(), 1)[0].strip()
                # Удаляем служебные символы и многоточие
                if job_desc_text.endswith('…'):
                    job_desc_text = job_desc_text[:-1].strip()
                parsed_data[VacancyAttrs.JOB_DESC.attr_id] = job_desc_text

            for key, value in parsed_data.items():
                print(VacancyAttrs.get_name_by_id(key), ': ', value)
            print()

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

    # soup = BeautifulSoup(html, 'lxml')
    # # Разделение HTML сообщения с несколькими вакансиями на отдельные части по тегам <td>,
    # # где в стиле содержится 'padding-bottom:24px'
    # style_filter = lambda value: (
    #         value and any('padding-bottom:24px' in part.strip().lower() for part in value.split(';')))
    # html_parts = soup.find_all('td', style=style_filter)

    result = MessageTypes.EMAIL_UNKNOWN
    soup = BeautifulSoup(email_html, 'lxml')
    for vacancy_signs in email_messages_signs.vacancy:
        if soup.find_all(vacancy_signs.tag,
                         attrs={vacancy_signs.attr_name: get_style_checker(vacancy_signs.attr_value)}):
            result = MessageTypes.EMAIL_VACANCY
    return result


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

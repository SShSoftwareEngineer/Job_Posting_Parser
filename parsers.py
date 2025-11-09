import re
from abc import ABC, abstractmethod
from typing import cast

from telethon.tl.types import Message

from config_handler import tg_vacancy_text_signs, regex_patterns, tg_statistic_text_signs
from configs.config import MessageSources
from telegram_handler import tg_detect_message_type
from utils import str_to_numeric


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
        message_type=tg_detect_message_type(message_text)
        parsed_data = {
            'date': message.date.astimezone(),
            'message_id': message.id,
            'email_uid': None,
            'text': message_text,
            'message_source_id': MessageSources.TELEGRAM.value,
            'message_type_id': message_type.get_message_type_id(message_type),
        }
        return parsed_data


class TgVacancyTextParser(MessageParser):
    """
    Класс для парсинга сообщений Telegram с вакансиями, возвращает словарь с результатами парсинга
    """

    def parse(self, text: str) -> dict:
        """
        Функция для парсинга сообщений Telegram с вакансиями, возвращает словарь с результатами парсинга
        """

        parsed_data = {}
        # Извлечение строк с необходимой информацией / Extracting lines with the necessary information
        strings = text.split('\n')
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
        matching = re.search(fr'{regex_patterns.salary_range}\Z', str_1)
        if matching:
            if len(matching.groups()) == 2:
                parsed_data['min_salary'] = cast(int | None, str_to_numeric(matching.group(1)))
                parsed_data['max_salary'] = cast(int | None, str_to_numeric(matching.group(2)))
        else:
            matching = re.search(fr'{regex_patterns.salary}\Z', str_1)
            if matching:
                parsed_data['min_salary'] = cast(int | None, str_to_numeric(matching.group(1)))
                parsed_data['max_salary'] = parsed_data['min_salary']
        # Extracting full vacancy text URL on the website from the Telegram message text
        # Извлечение URL вакансии на сайте из текста сообщения Telegram
        matching = re.search(regex_patterns.url, text)
        if matching:
            parsed_data['url'] = matching.group(0)
        # Extracting subscription to job vacancy messages from the Telegram message text
        # Извлечение информации о подписке рассылки из текста сообщения Telegram
        matching = re.sub(f'{"|".join(tg_vacancy_text_signs.subscription)}', '', str_last)
        if matching:
            parsed_data['subscription'] = matching.strip('\"\' *_`')
        return parsed_data


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
        return parsed_data


if __name__ == '__main__':
    pass

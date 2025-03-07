""" Модуль предназначен для работы с файлом конфигурации и содержит константы и классы для работы с ним
TABLE_NAMES - словарь с именами таблиц БД для разных типов сообщений
HtmlClasses - содержит названия классов HTML-тегов, которые соответствуют требуемым блокам HTML файла сообщения с сайта
HtmlParsingSigns - содержит сигнатуры классов для парсинга HTML файла сообщения с сайта
VacancyMessageConfig - содержит сигнатуры для парсинга сообщений Telegram с вакансией и HTML файла сообщения с сайта
StatisticMessageConfig - содержит сигнатуры для парсинга сообщений Telegram со статистикой
MessageConfig - содержит сигнатуры для парсинга сообщений
ExportToExcelConfig - содержит конфигурации для экспорта результатов в формат MS Excel
RePatternsConfig - содержит шаблоны модуля RE для извлечения текстовой информации
Config - корневой класс конфигурации
config - объект Config, содержащий конфигурацию, считываемую из файла JSON
"""

import json
from typing import List, Dict
from pydantic import BaseModel, ValidationError

# Имя файла конфигурации в формате JSON
_CONFIG_FILE_NAME = 'config.json'

# Имена таблиц в базе данных для разных типов сообщений
TABLE_NAMES = {'vacancy': 'vacancy_msgs',
               'statistic': 'statistic_msgs',
               'service': 'service_msgs',
               'source': 'source_msgs'}


class HtmlClasses(BaseModel):
    """ Содержит названия классов HTML-тегов, которые соответствуют требуемым блокам HTML файла сообщения с сайта

    Attributes:
    description (str): HTML-класс описания вакансии
    job_card (str): HTML-класс карточки вакансии
    ul_tags (str): HTML-класс тегов разметки карточки вакансии
    """
    description: str
    job_card: str
    ul_tags: str


class HtmlParsingSigns(BaseModel):
    """ Класс содержит сигнатуры для парсинга HTML файла сообщения с сайта

    Attributes:
    html_classes (HtmlClasses): названия классов HTML-тегов,
        которые соответствуют нужным блокам HTML файла сообщения с сайта
    candidate_locations (List[str]): сигнатуры для определения локаций кандидатов
    domain (List[str]):  сигнатуры для определения домена компании
    offices (List[str]):  сигнатуры для определения местоположения офисов компании
    """
    html_classes: HtmlClasses
    lingvo: List[str]
    experience: List[str]
    candidate_locations: List[str]
    work_type: List[str]
    domain: List[str]
    company_type: List[str]
    offices: List[str]


class VacancyMessageConfig(BaseModel):
    """ Класс содержит сигнатуры для парсинга сообщений Telegram с вакансией и HTML файла сообщения с сайта

    Attributes:
    text_parsing_signs - сигнатуры для парсинга сообщений Telegram с вакансией
    html_parsing_signs - сигнатуры для парсинга HTML файла сообщения с сайта
    """
    text_parsing_signs: Dict[str, List[str]]
    html_parsing_signs: HtmlParsingSigns


class StatisticMessageConfig(BaseModel):
    """ Класс содержит сигнатуры для парсинга сообщений Telegram со статистикой

    Attributes:
    text_parsing_signs - сигнатуры для парсинга сообщений Telegram со статистикой
    """
    text_parsing_signs: Dict[str, List[str]]


class MessageConfigs(BaseModel):
    """ Класс содержит сигнатуры для парсинга сообщений

    Attributes:
    vacancy (VacancyMessageConfig) - сигнатуры для парсинга сообщений с вакансией
    statistic (StatisticMessageConfig) - сигнатуры для парсинга сообщений со статистикой
    """
    vacancy: VacancyMessageConfig
    statistic: StatisticMessageConfig


class ExportToExcelConfig(BaseModel):
    """ Класс конфигурации для экспорта результатов в формат MS Excel

    Attributes:
    sheet_name (str): имя листа файла MS Excel
    sql (str): SQL запрос
    columns (Dict[str, str]): названия колонок, которые включаются в SQL запрос и их отображаемые имена
    """
    sheet_name: str
    sql: str
    columns: Dict[str, str]


class RePatternsConfig(BaseModel):
    """ Класс содержит шаблоны модуля RE для извлечения текстовой информации

    Attributes:
    url (str): шаблон RE URL полного текста вакансии на сайте
    numeric (str): шаблон RE для чисел (+, -, int, float)
    salary (str): шаблон RE для заработной платы
    salary_range (str): шаблон RE для диапазона заработной платы
    """
    url: str
    numeric: str
    salary: str
    salary_range: str


class Config(BaseModel):
    """ Корневой класс конфигурации

    Attributes:
    message_signs (Dict[str, List[str]]): сигнатуры для распознавания типа сообщения
    message_configs (Dict[str, MessageConfig]): сигнатуры для парсинга
    export_to_excel (Dict[str, ExportToExcelConfig]): конфигурации экспорта результатов в формат MS Excel
    re_patterns (RePatternsConfig): шаблоны модуля RE для извлечения текстовой информации
    Methods:
    resolve_patterns(self): Заменяет placeholders в конфигурации, подставляя реальные значения
    get_url_pattern(self) -> str: Возвращает шаблон модуля RE для URL полного сообщения о вакансии на сайте
    get_vacancy_pattern(self) -> str: Возвращает шаблон RE из разделителей для сообщений с несколькими вакансиями
    get_export_to_excel_sql(self, table_name: str) -> str: Возвращает SQL запрос для экспорта
        информации в файл формата MS Excel
    """
    message_signs: Dict[str, List[str]]
    message_configs: MessageConfigs
    export_to_excel: Dict[str, ExportToExcelConfig]
    re_patterns: RePatternsConfig

    def resolve_patterns(self):
        """ Заменяет placeholders в конфигурации, подставляя реальные значения """
        # Заменяет placeholders в шаблонах модуля RE
        self.re_patterns.salary = self.re_patterns.salary.replace('{numeric_pattern}',
                                                                  self.re_patterns.numeric)
        self.re_patterns.salary_range = self.re_patterns.salary_range.replace('{numeric_pattern}',
                                                                              self.re_patterns.numeric)
        # Заменяет placeholders в названиях таблиц в SQL запросах
        for key in TABLE_NAMES:
            self.export_to_excel[key].sql = self.get_export_to_excel_sql(key)

    def get_url_pattern(self) -> str:
        """ Возвращает шаблон модуля RE для URL полного сообщения о вакансии на сайте """
        return self.re_patterns.url

    def get_vacancy_pattern(self) -> str:
        """ Возвращает шаблон RE из разделителей для сообщений с несколькими вакансиями """
        patterns = getattr(self.message_configs.vacancy.text_parsing_signs, 'splitter_pattern', [])
        return fr'([\s\S]*?(?:{"|".join(patterns)}).*)(?:\n\n)?'

    def get_export_to_excel_sql(self, table_name: str) -> str:
        """ Возвращает SQL запрос для экспорта информации в файл формата MS Excel """
        sql = f"SELECT {', '.join(self.export_to_excel[table_name].columns.keys())} FROM {table_name}"
        if table_name != 'source':
            sql += f" JOIN source ON source.message_id = {table_name}.message_id"
        for key, value in TABLE_NAMES.items():
            sql = sql.replace(key, value)
        return sql


def _read_config_data(config_file_name: str) -> Config:
    """ Загружает конфигурацию из JSON файла и возвращает объект Config

    Arguments:
    config_file_name (str): имя JSON файла конфигурации
    Returns:
    Config - объект Config
    """
    with open(config_file_name, 'r', encoding='utf-8') as file:
        config_data = json.load(file)

    try:
        result = Config(**config_data)
        return result
    except ValidationError as e:
        print(f'Error Description\n{e.json()}\n')
        raise ValueError("Config validation failed") from e


# Загружает конфигурацию из файла и заменяет плейсхолдеры
config = _read_config_data(_CONFIG_FILE_NAME)
config.resolve_patterns()

if __name__ == '__main__':
    pass

""" The module is designed to work with a configuration file and contains constants and classes for working with it.

TABLE_NAMES - dictionary with database table names for different message types
HtmlClasses - names of HTML tag classes that correspond to required blocks in the HTML message file from the website
HtmlParsingSigns - class signatures for parsing HTML message files from the website
VacancyMessageConfig - signatures for parsing Telegram vacancy messages and HTML message files from the website
StatisticMessageConfig - signatures for parsing Telegram statistics messages
MessageConfig - signatures for parsing messages
ExportToExcelConfig - configurations for exporting results to MS Excel format
RePatternsConfig - regular expressions (patterns) for extracting text information
Config - the root configuration class
config - an object of the Config class containing the configuration read from a JSON file
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
    """ Класс содержит названия классов HTML-тегов, которые соответствуют требуемым блокам HTML файла сообщения с сайта

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
        которые соответствуют требуемым блокам HTML файла сообщения с сайта
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
    vacancy (VacancyMessageConfig) - сигнатуры для парсинга сообщений с вакансиями
    statistic (StatisticMessageConfig) - сигнатуры для парсинга сообщений со статистикой
    """
    vacancy: VacancyMessageConfig
    statistic: StatisticMessageConfig


class ExportToExcelConfig(BaseModel):
    """ Класс конфигурации для экспорта результатов в формат Microsoft Excel

    Attributes:
    sheet_name (str): имя листа в файле Microsoft Excel
    sql (str): SQL запрос
    columns (Dict[str, str]): названия колонок, которые включаются в SQL запрос и их отображаемые имена
    """
    sheet_name: str
    sql: str
    columns: Dict[str, str]


class RePatternsConfig(BaseModel):
    """ Класс содержит регулярные выражения (шаблоны) для извлечения текстовой информации

    Attributes:
    url (str): шаблон URL полного текста вакансии на сайте
    numeric (str): шаблон для чисел (+, -, int, float)
    salary (str): шаблон для заработной платы
    salary_range (str): шаблон для диапазона заработной платы
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
    re_patterns (RePatternsConfig): регулярные выражения (шаблоны) для извлечения текстовой информации
    Methods:
    resolve_patterns(self): Заменяет placeholders в конфигурации, подставляя реальные значения
    get_url_pattern(self) -> str: Возвращает шаблон для URL полного сообщения о вакансии на сайте
    get_vacancy_pattern(self) -> str: Возвращает шаблон из разделителей для сообщений с несколькими вакансиями
    get_export_to_excel_sql(self, table_name: str) -> str: Возвращает SQL запрос для экспорта
        информации в файл формата MS Excel
    """
    message_signs: Dict[str, List[str]]
    message_configs: MessageConfigs
    export_to_excel: Dict[str, ExportToExcelConfig]
    re_patterns: RePatternsConfig

    def resolve_patterns(self):
        """ Заменяет placeholders в конфигурации, подставляя реальные значения """
        # Заменяет placeholders в регулярных выражениях (шаблонах)
        self.re_patterns.salary = self.re_patterns.salary.replace('{numeric_pattern}',
                                                                  self.re_patterns.numeric)
        self.re_patterns.salary_range = self.re_patterns.salary_range.replace('{numeric_pattern}',
                                                                              self.re_patterns.numeric)
        # Заменяет placeholders в названиях таблиц в SQL запросах
        for key in TABLE_NAMES:
            self.export_to_excel[key].sql = self.get_export_to_excel_sql(key)

    def get_url_pattern(self) -> str:
        """ Возвращает регулярное выражение (шаблон) для URL полного сообщения о вакансии на сайте """
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

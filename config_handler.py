"""
The module is designed to work with a configuration file and contains constants and classes for working with it.

TABLE_NAMES: dictionary with database table names for different message types
HtmlClasses: names of HTML tag classes that correspond to required blocks in the HTML message file from the website
HtmlParsingSigns: signatures for parsing HTML message files from the website
VacancyMessageConfig: signatures for parsing Telegram vacancy messages and HTML message files from the website
StatisticMessageConfig: signatures for parsing Telegram statistics messages
MessageConfig: signatures for parsing vacancy and statistics messages
ExportToExcelConfig: configuration for exporting results to MS Excel format
RePatternsConfig: regular expressions (patterns) for extracting text information
Config: the root configuration class
config: an object of the Config class containing the configuration read from a JSON file
"""

import json
from typing import List, Dict
from pydantic import BaseModel, ValidationError

# Configuration file name in JSON format / Имя файла конфигурации в формате JSON
_CONFIG_FILE_NAME = 'configs/config.json'

# Table names in the database for different types of messages / Имена таблиц в базе данных для разных типов сообщений
TABLE_NAMES = {'vacancy': 'vacancy_msgs',
               'statistic': 'statistic_msgs',
               'service': 'service_msgs',
               'source': 'source_msgs'}


class HtmlClasses(BaseModel):
    """
    Names of HTML tag classes that correspond to required blocks in the HTML message file from the website

    Названия классов HTML-тегов, которые соответствуют требуемым блокам HTML файла сообщения с сайта

    Attributes:
    description (str): vacancy description HTML class
    job_card (str): job card HTML class
    ul_tags (str): job card markup tags HTML class
    """
    description: str
    job_card: str
    ul_tags: str


class HtmlParsingSigns(BaseModel):
    """
    Signatures for parsing HTML message files from the website

    Сигнатуры для парсинга HTML файла сообщения с сайта

    Attributes:
    html_classes (HtmlClasses): names of HTML tag classes that correspond to required
        blocks of the HTML message file from the website
    candidate_locations (List[str]): signatures for determining candidate locations
    domain (List[str]): signatures for determining the company domain
    offices (List[str]): signatures for determining company office locations
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
    """
    Signatures for parsing Telegram vacancy messages and HTML message files from the website

    Сигнатуры для парсинга сообщений Telegram с вакансией и HTML файла сообщения с сайта

    Attributes:
    text_parsing_signs (Dict[str, List[str]]): signatures for parsing Telegram vacancy messages
    html_parsing_signs (HtmlParsingSigns): signatures for parsing HTML message file from the website
    """
    text_parsing_signs: Dict[str, List[str]]
    html_parsing_signs: HtmlParsingSigns


class StatisticMessageConfig(BaseModel):
    """
    Signatures for parsing Telegram statistics messages

    Сигнатуры для парсинга сообщений Telegram со статистикой

    Attributes:
    text_parsing_signs (Dict[str, List[str]]): signatures for parsing Telegram statistics messages
    """
    text_parsing_signs: Dict[str, List[str]]


class MessageConfigs(BaseModel):
    """
    Signatures for parsing vacancy and statistics messages

    Сигнатуры для парсинга сообщений с вакансиями и со статистикой

    Attributes:
    vacancy (VacancyMessageConfig): signatures for parsing vacancy messages
    statistic (StatisticMessageConfig): signatures for parsing statistics messages
    """
    vacancy: VacancyMessageConfig
    statistic: StatisticMessageConfig


class ExportToExcelConfig(BaseModel):
    """
    Configuration for exporting results to MS Excel format

    Конфигурация для экспорта результатов в формат Microsoft Excel

    Attributes:
    sheet_name (str): sheet name in Microsoft Excel file
    sql (str): SQL query
    columns (Dict[str, str]): column names that are included in the SQL query and their display names
    """
    sheet_name: str
    sql: str
    columns: Dict[str, str]


class RePatternsConfig(BaseModel):
    """
    Regular expressions (patterns) for extracting text information

    Регулярные выражения (шаблоны) для извлечения текстовой информации

    Attributes:
    url (str): full vacancy text URL on the website pattern
    numeric (str): numeric pattern (+, -, int, float)
    salary (str): salary pattern
    salary_range (str): salary range pattern
    """
    url: str
    numeric: str
    salary: str
    salary_range: str


class Config(BaseModel):
    """
    The root configuration class

    Корневой класс конфигурации

    Attributes:
    message_signs (Dict[str, List[str]]): signatures for message type recognition
    message_configs (Dict[str, MessageConfig]): signatures for parsing vacancy and statistics messages
    export_to_excel (Dict[str, ExportToExcelConfig]): configuration for exporting results to MS Excel format
    re_patterns (RePatternsConfig): regular expressions (patterns) for extracting text information
    Methods:
    resolve_patterns(self): replaces placeholders in the configuration with real values
    get_url_pattern(self) -> str: returns a template for the URL of the full job posting on the website
    get_vacancy_pattern(self) -> str: returns a template of separators for messages containing multiple job vacancies
    get_export_to_excel_sql(self, table_name: str) -> str: returns an SQL query for exporting
        information to an MS Excel file
    """
    message_signs: Dict[str, List[str]]
    message_configs: MessageConfigs
    export_to_excel: Dict[str, ExportToExcelConfig]
    re_patterns: RePatternsConfig

    def resolve_patterns(self):
        """ Replaces placeholders in the configuration with real values
            Заменяет placeholders в конфигурации, подставляя реальные значения """
        # Заменяет placeholders в регулярных выражениях (шаблонах)
        self.re_patterns.salary = self.re_patterns.salary.replace('{numeric_pattern}',
                                                                  self.re_patterns.numeric)
        self.re_patterns.salary_range = self.re_patterns.salary_range.replace('{numeric_pattern}',
                                                                              self.re_patterns.numeric)
        # Заменяет placeholders в названиях таблиц в SQL запросах
        for key in TABLE_NAMES:
            self.export_to_excel[key].sql = self.get_export_to_excel_sql(key)

    def get_url_pattern(self) -> str:
        """ Returns a template for the URL of the full job posting on the website
            Возвращает регулярное выражение (шаблон) для URL полной вакансии на сайте """
        return self.re_patterns.url

    def get_vacancy_pattern(self) -> str:
        """ Returns a template of separators for messages containing multiple job vacancies
            Возвращает регулярное выражение (шаблон) из разделителей для сообщений с несколькими вакансиями """
        patterns = self.message_configs.vacancy.text_parsing_signs.get('splitter_pattern', [])
        return fr'([\s\S]*?(?:{"|".join(patterns)}).*)(?:\n\n)?'

    def get_export_to_excel_sql(self, table_name: str) -> str:
        """ Returns an SQL query for exporting information to an MS Excel file
            Возвращает SQL запрос для экспорта информации в файл формата MS Excel """
        sql = f"SELECT {', '.join(self.export_to_excel[table_name].columns.keys())} FROM {table_name}"
        if table_name != 'source':
            sql += f" JOIN source ON source.message_id = {table_name}.message_id"
        for key, value in TABLE_NAMES.items():
            sql = sql.replace(key, value)
        return sql


def _read_config_data(config_file_name: str) -> Config:
    """
    Loads the configuration from a JSON file and returns a Config object

    Загружает конфигурацию из JSON файла и возвращает объект Config

    Arguments:
    config_file_name (str): the name of the JSON configuration file
    Returns:
    Config: Config object
    """
    with open(config_file_name, 'r', encoding='utf-8') as file:
        config_data = json.load(file)
    try:
        result = Config(**config_data)
        return result
    except ValidationError as e:
        print(f'Error Description\n{e.json()}\n')
        raise ValueError("Config validation failed") from e


# Loads the configuration from a JSON file and replaces placeholders with real values
# Загружает конфигурацию из файла и заменяет плейсхолдеры реальными значениями
config = _read_config_data(_CONFIG_FILE_NAME)
config.resolve_patterns()

if __name__ == '__main__':
    pass

""" Модуль предназначен для работы с файлом конфигурации, который содержит
1. _CONFIG_FILE_NAME - имя файла конфигурации в формате JSON
2. TABLE_NAMES - словарь с именами таблиц БД
3. Классы pydantic для JSON файла конфигурации

Иерархия классов:

class Config
    message_signs - сигнатуры для распознавания типа сообщения
    message_configs: class MessageConfig - сигнатуры для парсинга
    export_to_excel: class ExportToExcelConfig - конфигурации экспорта результатов в формат MS Excel
    re_patterns: class RePatternsConfig - шаблоны модуля RE для извлечения текстовой информации

    class MessageConfig
        text_parsing_signs: class TextParsingSigns - сигнатуры для парсинга текстовых сообщений Telegram
        html_parsing_signs: class HtmlParsingSigns - сигнатуры для парсинга HTML файла сообщения с сайта

        class TextParsingSigns
            поля: сигнатуры

        class HtmlParsingSigns
            html_classes: class HtmlClasses - названия классов HTML-тегов, которые соответствуют
                                              нужным блокам HTML файла сообщения с сайта
            поля: сигнатуры

            class HtmlClasses
                имена классов: классы

    class ExportToExcelConfig
        имя листа Excel
        соответствующий запрос для БД
        названия колонок, которые включаются в запрос и их отображаемые имена

    class RePatternsConfig
        шаблоны URL, чисел, заработной платы, диапазона зарплаты

"""

import json
from typing import Optional, List, Dict
from pydantic import BaseModel, ValidationError

# Имя файла конфигурации в формате JSON
_CONFIG_FILE_NAME = 'config.json'

# Имена таблиц в базе данных для разных типов сообщений
TABLE_NAMES = {'vacancy': 'vacancy_msgs',
               'statistic': 'statistic_msgs',
               'service': 'service_msgs',
               'source': 'source_msgs'}


class TextParsingSigns(BaseModel):
    """ Класс содержит сигнатуры для парсинга текстовых сообщений Telegram
    Attributes:
        position_company (Optional[str]): позиция, компания
        location_experience (Optional[List[str]]): локация, опыт
        vacancies_in_30d (Optional[List[str]]): кол-во вакансий за 30 дней
        candidates_online (Optional[List[str]]): кандидатов онлайн
        salary (Optional[List[str]]): заработная плата
        responses_to_vacancies (Optional[List[str]]): откликов на вакансию
        vacancies_per_week (Optional[List[str]]): вакансий за неделю
        candidates_per_week (Optional[List[str]]): кандидатов за неделю
        subscription (Optional[List[str]]): подписка
        splitter_pattern (Optional[List[str]]): разделитель вакансий в одном сообщении
    """
    position_company: Optional[str] = None
    location_experience: Optional[List[str]] = None
    vacancies_in_30d: Optional[List[str]] = None
    candidates_online: Optional[List[str]] = None
    salary: Optional[List[str]] = None
    responses_to_vacancies: Optional[List[str]] = None
    vacancies_per_week: Optional[List[str]] = None
    candidates_per_week: Optional[List[str]] = None
    subscription: Optional[List[str]] = None
    splitter_pattern: Optional[List[str]] = None


class HtmlClasses(BaseModel):
    """ Класс содержит названия классов HTML-тегов, которые соответствуют
        требуемым блокам HTML файла сообщения с сайта
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
        html_classes (Optional[HtmlClasses]): названия классов HTML-тегов,
            которые соответствуют нужным блокам HTML файла сообщения с сайта
        candidate_locations (List[str]): сигнатуры для определения локаций кандидатов
        domain (List[str]):  сигнатуры для определения домена компании
        offices (List[str]):  сигнатуры для определения местоположения офисов компании
    """
    html_classes: Optional[HtmlClasses]
    candidate_locations: List[str]
    domain: List[str]
    offices: List[str]


class MessageConfig(BaseModel):
    """ Класс содержит сигнатуры для парсинга сообщений
    Attributes:
        text_parsing_signs (Optional[TextParsingSigns]): сигнатуры для парсинга текстовых сообщений Telegram
        html_parsing_signs (Optional[HtmlParsingSigns]): сигнатуры для парсинга HTML файла сообщения с сайта
    """
    text_parsing_signs: Optional[TextParsingSigns] = None
    html_parsing_signs: Optional[HtmlParsingSigns] = None


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
        resolve_patterns(self):
            Заменяет placeholders в конфигурации, подставляя реальные значения
        get_url_pattern(self) -> str:
            Возвращает шаблон модуля RE для URL полного сообщения о вакансии на сайте
        get_vacancy_pattern(self) -> str
            Возвращает шаблон RE из разделителей для сообщений с несколькими вакансиями
        get_export_to_excel_sql(self, table_name: str) -> str:
            Возвращает SQL запрос для экспорта информации в файл формата MS Excel
    """
    message_signs: Dict[str, List[str]]
    message_configs: Dict[str, MessageConfig]
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
        patterns = getattr(self.message_configs['vacancy'].text_parsing_signs, 'splitter_pattern', [])
        return fr'([\s\S]*?(?:{"|".join(patterns)}).*)(?:\n\n)?'

    def get_export_to_excel_sql(self, table_name: str) -> str:
        """ Возвращает SQL запрос для экспорта информации в файл формата MS Excel """
        sql = f"SELECT {', '.join(self.export_to_excel[table_name].columns.keys())} FROM {table_name}"
        if table_name != 'source':
            sql += f" JOIN source ON source.message_id = {table_name}.message_id"
        for key, value in TABLE_NAMES.items():
            sql = sql.replace(key, value)
        return sql


def read_config_data(config_file_name: str) -> Config:
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


config = read_config_data(_CONFIG_FILE_NAME)
config.resolve_patterns()

if __name__ == '__main__':
    pass

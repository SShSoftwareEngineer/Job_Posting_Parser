"""
The module is designed to work with a configuration file and contains constants and classes for working with it.

Config: the root configuration class
MessageConfig: signatures for parsing vacancy and statistics messages
ExportToExcel: configuration for exporting results to MS Excel format
RePatterns: regular expressions (patterns) for extracting text information
HtmlParsingSigns: signatures for parsing HTML message files from the website
VacancyMessage: signatures for parsing Telegram vacancy messages and HTML message files from the website
StatisticMessage: signatures for parsing Telegram statistics messages
HtmlClasses: names of HTML tag classes that correspond to required blocks in the HTML message file from the website
config: an object of the Config class containing the configuration read from a JSON file
"""

import json
import tomllib
from pydantic import BaseModel, ValidationError
from configs.config import GlobalConst, TableNames

with open('config.toml', 'rb') as f:
    config_toml = tomllib.load(f)


class TgMessagesSigns(BaseModel):
    tg_vacancy: list[str]
    tg_statistic: list[str]
    tg_service: list[str]


tg_messages_signs = None
try:
    tg_messages_signs = TgMessagesSigns(**config_toml.get('tg_messages_signs', {}))
except ValidationError as err:
    print(f'Error in [tg_messages_signs] section: {err}')


class TgVacancyTextSigns(BaseModel):
    position_company: list[str]
    location_experience: list[str]
    subscription: list[str]
    splitter_pattern: list[str]


tg_vacancy_text_signs = None
try:
    tg_vacancy_text_signs = TgVacancyTextSigns(**config_toml.get('tg_vacancy_text_signs', {}))
except ValidationError as err:
    print(f'Error in [tg_vacancy_text_signs] section: {err}')


class TgStatisticTextSigns(BaseModel):
    vacancies_in_30d: list[str]
    candidates_online: list[str]
    salary: list[str]
    responses_to_vacancies: list[str]
    vacancies_per_week: list[str]
    candidates_per_week: list[str]


tg_statistic_text_signs = None
try:
    tg_statistic_text_signs = TgStatisticTextSigns(**config_toml.get('tg_statistic_text_signs', {}))
except ValidationError as err:
    print(f'Error in [tg_statistic_text_signs] section: {err}')


class RegexPatterns(BaseModel):
    url: str
    numeric: str
    salary: str
    salary_range: str


regex_patterns = None
try:
    regex_patterns = RegexPatterns(**config_toml.get('regex_patterns', {}))
except ValidationError as err:
    print(f'Error in [regex_patterns] section: {err}')

regex_patterns.salary = regex_patterns.salary.replace('{numeric_pattern}', regex_patterns.numeric)
regex_patterns.salary_range = regex_patterns.salary_range.replace('{numeric_pattern}', regex_patterns.numeric)


class Selector(BaseModel):
    tag: str
    attr_name: str
    attr_value: list[str]


class EmailMessagesSigns(BaseModel):
    vacancy: list[Selector]


email_messages_signs = None
try:
    email_messages_signs = EmailMessagesSigns(**config_toml.get('email_messages_signs', {}))
except ValidationError as err:
    print(f'Error in [email_messages_signs] section: {err}')


class EmailVacancySelVer0(BaseModel):
    position_url_selector: Selector
    company_selector: Selector
    location_experience_salary_selector: Selector
    salary_selector: Selector
    job_desc_prev_selector: Selector
    splitter_selectors: list[Selector]


email_vacancy_sel_0 = None
try:
    email_vacancy_sel_0 = EmailVacancySelVer0(**config_toml.get('email_vacancy_sel_0', {}))
except ValidationError as err:
    print(f'Error in [email_vacancy_sel_0] section: {err}')


class EmailVacancySelVer1(BaseModel):
    splitter_selector: Selector
    position_url_selector: str
    salary_selector: str
    company_div_selector: Selector
    company_span_selector: Selector
    experience_lingvo_worktype_location_selector: Selector
    job_desc_prev_selector: Selector
    subscription_selector: Selector


email_vacancy_sel_1 = None
try:
    email_vacancy_sel_1 = EmailVacancySelVer1(**config_toml.get('email_vacancy_sel_1', {}))
except ValidationError as err:
    print(f'Error in [email_vacancy_sel_1] section: {err}')


class Repls(BaseModel):
    repl: list[dict[str, list[str]]] = []  # replacement patterns
    remove: list[str] = []  # remove patterns


class EmailVacancyRepls(BaseModel):
    pos_comp: Repls
    job_desc_prev: Repls
    subscription: Repls


email_vacancy_repls = None
try:
    email_vacancy_repls = EmailVacancyRepls(**config_toml.get('email_vacancy_repls', {}))
except ValidationError as err:
    print(f'Error in [email_vacancy_repls] section: {err}')


class WebVacancySel(BaseModel):
    position_selector: str
    company_selector: str
    job_desc_selector: Selector
    url_selector: Selector
    main_tech_selector: str
    more_tech_stack_selector: Selector
    second_tech_stack_selector: str
    job_card_selector: str


web_vacancy_sel = None
try:
    web_vacancy_sel = WebVacancySel(**config_toml.get('web_vacancy_sel', {}))
except ValidationError as err:
    print(f'Error in [web_vacancy_sel] section: {err}')


class WebVacancyRepls(BaseModel):
    experience: Repls
    lingvo: Repls
    employment: Repls
    domain: Repls
    company_type: Repls
    offices: Repls
    candidate_locations: Repls
    notes: Repls


web_vacancy_repls = None
try:
    web_vacancy_repls = WebVacancyRepls(**config_toml.get('web_vacancy_repls', {}))
except ValidationError as err:
    print(f'Error in [web_vacancy_repls] section: {err}')

pass


def resolve_patterns():
    """
    Replaces placeholders in the configuration with real values
    Заменяет placeholders в конфигурации, подставляя реальные значения
    """

    # Replaces placeholders in regular expressions (templates)
    # Заменяет placeholders в регулярных выражениях (шаблонах)
    regex_patterns.salary = regex_patterns.salary.replace('{numeric_pattern}', regex_patterns.numeric)
    regex_patterns.salary_range = regex_patterns.salary_range.replace('{numeric_pattern}', regex_patterns.numeric)

    # # Replaces placeholders in table names in SQL queries / Заменяет placeholders в названиях таблиц в SQL запросах
    # for item in self.export_to_excel.keys():
    #     self.export_to_excel[item].sql = self.get_export_to_excel_sql(item)


# -----------------------------------------------------------------------------------------------------------

class Config(BaseModel):
    """
    The root configuration class
    Корневой класс конфигурации
    Attributes:
        tg_message_signs (dict[str, list[str]]): signatures for message type recognition
        message_configs (dict[str, MessageConfig]): signatures for parsing vacancy and statistics messages
        export_to_excel (dict[str, ExportToExcel]): configuration for exporting results to MS Excel format
        re_patterns (RePatterns): regular expressions (patterns) for extracting text information
    """

    tg_message_signs: dict[str, list[str]]
    message_configs: 'MessageConfigs'
    export_to_excel: dict[str, 'ExportToExcel']
    re_patterns: 'RePatterns'

    def resolve_patterns(self):
        """
        Replaces placeholders in the configuration with real values
        Заменяет placeholders в конфигурации, подставляя реальные значения
        """

        # Replaces placeholders in regular expressions (templates)
        # Заменяет placeholders в регулярных выражениях (шаблонах)
        self.re_patterns.salary = self.re_patterns.salary.replace('{numeric_pattern}',
                                                                  self.re_patterns.numeric)
        self.re_patterns.salary_range = self.re_patterns.salary_range.replace('{numeric_pattern}',
                                                                              self.re_patterns.numeric)
        # Replaces placeholders in table names in SQL queries / Заменяет placeholders в названиях таблиц в SQL запросах
        for item in self.export_to_excel.keys():
            self.export_to_excel[item].sql = self.get_export_to_excel_sql(item)

    def get_url_pattern(self) -> str:
        """
        Returns a template for the URL of the full job posting on the website
        Возвращает регулярное выражение (шаблон) для URL полной вакансии на сайте
        """
        return self.re_patterns.url

    def get_vacancy_pattern(self) -> str:
        """
        Returns a template of separators for messages containing multiple job vacancies
        Возвращает регулярное выражение (шаблон) из разделителей для сообщений с несколькими вакансиями
        """
        patterns = self.message_configs.vacancy.text_parsing_signs.get('splitter_pattern', [])
        return fr'([\s\S]*?(?:{"|".join(patterns)}).*)(?:\n\n)?'

    def get_export_to_excel_sql(self, table_name: str) -> str:
        """
        Returns an SQL query for exporting information to an MS Excel file
        Возвращает SQL запрос для экспорта информации в файл формата MS Excel
        Attributes:
            table_name (str): current table name
        """

        sql = f"SELECT {', '.join(self.export_to_excel[table_name].columns.keys())} FROM {table_name}"
        if table_name != TableNames.RAW_MESSAGES:
            sql += f" JOIN source ON source.message_id = {table_name}.message_id"
        for item in TableNames:
            sql = sql.replace(item.name, item.value)
        return sql


class MessageConfigs(BaseModel):
    """
    Signatures for parsing vacancy and statistics messages
    Сигнатуры для парсинга сообщений с вакансиями и со статистикой
    Attributes:
        vacancy (VacancyMessage): signatures for parsing vacancy messages
        statistic (StatisticMessage): signatures for parsing statistics messages
    """
    vacancy: 'VacancyMessage'
    statistic: 'StatisticMessage'


class VacancyMessage(BaseModel):
    """
    Signatures for parsing Telegram vacancy messages and HTML message files from the website
    Сигнатуры для парсинга сообщений Telegram с вакансией и HTML файла сообщения с сайта
    Attributes:
        text_parsing_signs (dict[str, list[str]]): signatures for parsing Telegram vacancy messages
        html_parsing_signs (HtmlParsingSigns): signatures for parsing HTML message file from the website
    """

    text_parsing_signs: dict[str, list[str]]
    html_parsing_signs: 'HtmlParsingSigns'


class HtmlParsingSigns(BaseModel):
    """
    Signatures for parsing HTML message files from the website
    Сигнатуры для парсинга HTML файла сообщения с сайта
    Attributes:
        html_classes (HtmlClasses): names of HTML tag classes that correspond to required
            blocks of the HTML message file from the website
        candidate_locations (list[str]): signatures for determining candidate locations
        domain (list[str]): signatures for determining the company domain
        offices (list[str]): signatures for determining company office locations
    """

    html_classes: 'HtmlClasses'
    lingvo: list[str]
    experience: list[str]
    candidate_locations: list[str]
    employment: list[str]
    domain: list[str]
    company_type: list[str]
    offices: list[str]


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


class StatisticMessage(BaseModel):
    """
    Signatures for parsing Telegram statistics messages
    Сигнатуры для парсинга сообщений Telegram со статистикой
    Attributes:
        text_parsing_signs (dict[str, list[str]]): signatures for parsing Telegram statistics messages
    """
    text_parsing_signs: dict[str, list[str]]


class ExportToExcel(BaseModel):
    """
    Configuration for exporting results to MS Excel format
    Конфигурация для экспорта результатов в формат Microsoft Excel
    Attributes:
        sheet_name (str): sheet name in Microsoft Excel file
        sql (str): SQL query
        columns (dict[str, str]): column names that are included in the SQL query and their display names
    """

    sheet_name: str
    sql: str
    columns: dict[str, str]


class RePatterns(BaseModel):
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


def _read_config_data(config_file_name: str) -> Config:
    """
    Loads the configuration from a JSON file and returns a Config object
    Загружает конфигурацию из JSON файла и возвращает объект Config
    Attributes:
        config_file_name (str): the name of the JSON configuration file
    Returns:
        Config: Config object
    """

    with open(config_file_name, 'r', encoding='utf-8') as file:
        config_data = json.load(file)
    try:
        result = Config(**config_data)
        return result
    except ValidationError as err:
        print(f'Error Description\n{err.json()}\n')
        raise ValueError("Config validation failed") from err


# Loads the configuration from a file and creates a global config object
# Загружает конфигурацию из файла и создает глобальный объект config
config = _read_config_data(GlobalConst.parse_config_file)
# Replaces placeholders with actual values / Заменяет placeholders реальными значениями
config.resolve_patterns()

if __name__ == '__main__':
    pass

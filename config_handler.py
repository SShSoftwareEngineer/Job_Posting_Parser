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

# Loads the configuration from a file
# Загружает конфигурацию из файла
with open(GlobalConst.parse_config_file, 'rb') as f:
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

if __name__ == '__main__':
    pass

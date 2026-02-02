"""
Configuration handler module
Модуль обработчика конфигурации

Selector: model for describing HTML selectors
Repls: model for describing replacement and removal patterns
TgMessagesSigns: signatures for parsing Telegram messages
TgVacancyTextSigns: signatures for parsing Telegram vacancy messages
TgStatisticTextSigns: signatures for parsing Telegram statistics messages
EmailMessagesSigns: signatures for parsing E-mail messages
EmailVacancySelVer0: HTML selectors for parsing E-mail vacancy messages version 0
EmailVacancySelVer1: HTML selectors for parsing E-mail vacancy messages version 1
EmailVacancyRepls: replacement patterns for parsing E-mail vacancy messages
WebVacancySel: HTML selectors for parsing Web vacancy content
WebVacancyRepls: replacement patterns for parsing Web vacancy content
RegexPatterns: regular expression patterns for extracting text information
Config: the root configuration class
"""

import tomllib
from pydantic import BaseModel, ValidationError
from configs.config import GlobalConst


# Supporting models / Вспомогательные модели

class Selector(BaseModel):
    """
    Model for describing HTML selectors
    Модель для описания HTML селекторов
    """
    tag: str
    attr_name: str
    attr_value: list[str]


class Repls(BaseModel):
    """
    Model for describing replacement and removal patterns
    Модель для описания шаблонов замены и удаления
    """
    repl: list[dict[str, list[str]]] = []  # replacement patterns
    remove: list[str] = []  # remove patterns


# Models for processing Telegram messages / Модели для обработки сообщений Telegram

class TgMessagesSigns(BaseModel):
    """
    Model for describing signs in Telegram messages
    Модель для описания признаков в сообщениях Telegram
    """
    tg_vacancy: list[str]
    tg_statistic: list[str]
    tg_service: list[str]


class TgVacancyTextSigns(BaseModel):
    """
    Model for describing signs in Telegram vacancy messages
    Модель для описания признаков в сообщениях Telegram вакансий
    """
    position_company: list[str]
    location_experience: list[str]
    subscription: list[str]
    splitter_pattern: list[str]


class TgStatisticTextSigns(BaseModel):
    """
    Model for describing signs in Telegram statistics messages
    Модель для описания признаков в сообщениях Telegram статистики
    """
    vacancies_in_30d: list[str]
    candidates_online: list[str]
    salary: list[str]
    responses_to_vacancies: list[str]
    vacancies_per_week: list[str]
    candidates_per_week: list[str]


# Models for processing email messages / Модели для обработки E-mail сообщений

class EmailMessagesSigns(BaseModel):
    """
    Model for describing signs in E-mail messages
    Модель для описания признаков в E-mail сообщениях
    """
    vacancy: list[Selector]


class EmailVacancySelVer0(BaseModel):
    """
    Model for describing HTML selectors in E-mail vacancy messages version 0
    Модель для описания HTML селекторов в E-mail сообщениях вакансий версии 0
    """
    position_url_selector: Selector
    company_selector: Selector
    location_experience_salary_selector: Selector
    salary_selector: Selector
    job_desc_prev_selector: Selector
    splitter_selectors: list[Selector]


class EmailVacancySelVer1(BaseModel):
    """
    Model for describing HTML selectors in E-mail vacancy messages version 1
    Модель для описания HTML селекторов в E-mail сообщениях вакансий версии 1
    """
    splitter_selector: Selector
    position_url_selector: str
    salary_selector: str
    company_div_selector: Selector
    company_span_selector: Selector
    experience_lingvo_worktype_location_selector: Selector
    job_desc_prev_selector: Selector
    subscription_selector: Selector


class EmailVacancyRepls(BaseModel):
    """
    Model for describing replacement patterns in E-mail vacancy messages
    Модель для описания шаблонов замены в E-mail сообщениях вакансий
    """
    pos_comp: Repls
    job_desc_prev: Repls
    subscription: Repls


# Models for processing web content of job vacancies, e-mails / Модели для обработки Web-содержимого вакансий и E-mail

class WebVacancySel(BaseModel):
    """
    Model for describing HTML selectors in Web vacancy content
    Модель для описания HTML селекторов в Web содержимом вакансий
    """
    position_selector: str
    company_selector: str
    job_desc_selector: Selector
    url_selector: Selector
    main_tech_selector: str
    more_tech_stack_selector: Selector
    second_tech_stack_selector: str
    job_card_selector: str


class WebVacancyRepls(BaseModel):
    """
    Model for describing replacement patterns in Web vacancy content
    Модель для описания шаблонов замены в Web содержимом вакансий
    """
    experience: Repls
    lingvo: Repls
    employment: Repls
    domain: Repls
    company_type: Repls
    offices: Repls
    candidate_locations: Repls
    notes: Repls


# Models for working with regular expressions / Модели для работы с регулярными выражениями

class RegexPatterns(BaseModel):
    """
    Model for describing regular expression patterns
    Модель для описания шаблонов регулярных выражений
    """
    url: str
    numeric: str
    salary: str
    salary_range: str


# Root configuration model / Корневая модель конфигурации

class Config(BaseModel):
    """
    Root configuration model
    Корневая модель конфигурации
    """
    tg_messages_signs: TgMessagesSigns
    tg_vacancy_text_signs: TgVacancyTextSigns
    tg_statistic_text_signs: TgStatisticTextSigns
    email_messages_signs: EmailMessagesSigns
    email_vacancy_sel_0: EmailVacancySelVer0
    email_vacancy_sel_1: EmailVacancySelVer1
    email_vacancy_repls: EmailVacancyRepls
    web_vacancy_sel: WebVacancySel
    web_vacancy_repls: WebVacancyRepls
    regex_patterns: RegexPatterns


# Loads the configuration from a file / Загружаем конфигурацию из файла

def load_config() -> Config:
    """
    Loads the configuration from a TOML file and returns a Config object.
    Загружает конфигурацию из TOML файла и возвращает объект Config.
        Returns:
    Config: The configuration object.
    """
    config_path = GlobalConst.parse_config_file
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open('rb') as f:
        data = tomllib.load(f)
    try:
        config_obj = Config(**data)
        # Performing post-processing for regex_patterns / Выполняем постобработку для regex_patterns
        reg_pat = config_obj.regex_patterns
        reg_pat.salary = reg_pat.salary.replace('{numeric_pattern}', reg_pat.numeric)
        reg_pat.salary_range = reg_pat.salary_range.replace('{numeric_pattern}', reg_pat.numeric)
        return config_obj
    except ValidationError as err:
        print(f"CRITICAL: Configuration validation failed:\n{err}")
        # Add ‘from err’ to preserve context / Добавляем 'from err' для сохранения контекста
        raise SystemExit(1) from err


# Creating a general configuration object
# Создаем единый объект конфигурации
config = load_config()

if __name__ == '__main__':
    pass

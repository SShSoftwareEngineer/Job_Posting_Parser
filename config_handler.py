import json
from typing import Optional, List, Dict
from pydantic import BaseModel
from pydantic import ValidationError

_CONFIG_FILE = 'settings.json'

TABLE_NAMES = {'source_messages': 'source_msgs',
               'vacancy_messages': 'vacancy_msg',
               'statistic_messages': 'statistic_msgs',
               'service_messages': 'service_msgs'}


# Классы конфигурации pydantic


class TextParsingSigns(BaseModel):
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
    description: str
    job_card: str
    ul_tags: str


class HtmlParsingSigns(BaseModel):
    html_classes: Optional[HtmlClasses]
    candidate_locations: List[str]
    domain: List[str]
    offices: List[str]


class MessageConfig(BaseModel):
    text_parsing_signs: Optional[TextParsingSigns] = None
    html_parsing_signs: Optional[HtmlParsingSigns] = None


class RePatternsConfig(BaseModel):
    url: str
    numeric: str
    salary: str
    salary_range: str


class ExportToExcelConfig(BaseModel):
    sheet_name: str
    col_names: Dict[str, str]
    sql: str


class Config(BaseModel):
    message_signs: Dict[str, List[str]]
    message_configs: Dict[str, MessageConfig]
    export_to_excel: Dict[str, ExportToExcelConfig]
    re_patterns: RePatternsConfig

    def resolve_patterns(self):
        self.re_patterns.salary = self.re_patterns.salary.replace('{numeric_pattern}',
                                                                  self.re_patterns.numeric)
        self.re_patterns.salary_range = self.re_patterns.salary_range.replace('{numeric_pattern}',
                                                                              self.re_patterns.numeric)

    def get_splitter_pattern(self) -> List[str]:
        return self.message_configs['vacancy'].text_parsing_signs.splitter_pattern

    def get_url_pattern(self) -> str:
        return self.re_patterns.url

    def get_vacancy_pattern(self) -> str:
        patterns = self.message_configs['vacancy'].text_parsing_signs.splitter_pattern
        return fr'([\s\S]*?(?:{"|".join(patterns)}).*)(?:\n\n)?'


# Загрузка конфигурации базы данных из файла
def read_config_data():
    with open(_CONFIG_FILE, 'r', encoding='utf-8') as file:
        config_data = json.load(file)
    try:
        result = Config(**config_data)
        return result
    except ValidationError as e:
        print(f'Error Description\n{e.json()}\n')
        raise ValueError("Config validation failed") from e


config = read_config_data()
config.resolve_patterns()

if __name__ == '__main__':
    pass

import json
from typing import Optional, List, Dict
from pydantic import BaseModel
from pydantic import ValidationError

_CONFIG_FILE = 'settings.json'

TABLE_NAMES = {'vacancy': 'vacancy_msgs',
               'statistic': 'statistic_msgs',
               'service': 'service_msgs',
               'source': 'source_msgs'}


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
    sql: str
    columns: List[str]
    column_names: List[str]


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
        for key in TABLE_NAMES.keys():
            self.export_to_excel[key].sql = self.get_export_to_excel_sql(key)

    def get_splitter_pattern(self) -> List[str]:
        return self.message_configs['vacancy'].text_parsing_signs.splitter_pattern

    def get_url_pattern(self) -> str:
        return self.re_patterns.url

    def get_vacancy_pattern(self) -> str:
        patterns = self.message_configs['vacancy'].text_parsing_signs.splitter_pattern
        return fr'([\s\S]*?(?:{"|".join(patterns)}).*)(?:\n\n)?'

    def get_export_to_excel_sql(self, table_name: str) -> str:
        sql = f"SELECT {', '.join(self.export_to_excel[table_name].columns)} FROM {table_name}"
        if table_name != 'source':
            sql += f" JOIN source ON source.message_id = {table_name}.message_id"
        for key, value in TABLE_NAMES.items():
            sql = sql.replace(key, value)
        return sql


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

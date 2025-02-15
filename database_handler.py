import json
import re
from datetime import datetime
from typing import Any, Optional

from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Integer, ForeignKey, Text, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

_DB_DATA = dict()
_DB_DATA_FILE = 'settings.json'
_NUMERIC_PATTERN = '([-+]?(?:\d*[.,]\d+|\d+))'  # '([-+]?(?:\d+[.,]\d+|\d+|\.\d+))'
_SALARY_RANGE_PATTERN = f'\$?{_NUMERIC_PATTERN}-{_NUMERIC_PATTERN}'
_SALARY_PATTERN = f'\$?{_NUMERIC_PATTERN}'
_VACANCY_URL_PATTERN = 'https?:\/\/djinni.co\/.*'
_TABLE_NAMES = {'source_messages': 'source_msgs',
                'vacancy_messages': 'vacancy_msg',
                'statistic_messages': 'statistic_msgs',
                'service_messages': 'service_msgs'}


class Base(DeclarativeBase):
    pass


# Модель для архива исходных сообщений

class SourceMessage(Base):
    __tablename__ = _TABLE_NAMES['source_messages']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, unique=True)
    date: Mapped[datetime]
    message_type: Mapped[str] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    vacancy_message: Mapped["VacancyMessage"] = relationship(back_populates="source_message")
    statistic_message: Mapped["StatisticMessage"] = relationship(back_populates="source_message")
    service_message: Mapped["ServiceMessage"] = relationship(back_populates="source_message")

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        self._set_message_type(_DB_DATA['message_type_patterns'])

    def _set_message_type(self, patterns: dict):
        for message_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if pattern in self.text:
                    self.message_type = message_type
                    return None


class VacancyMessage(Base):
    __tablename__ = _TABLE_NAMES['vacancy_messages']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{_TABLE_NAMES['source_messages']}.message_id'))
    source_message: Mapped[SourceMessage] = relationship(back_populates='vacancy_message')
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subscription: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_header: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    work_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    candidate_locations: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    main_tech: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tech_stack: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    offices: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        vacancy_signs = _DB_DATA['parsing_signs']['vacancy']
        self._set_position_company(vacancy_signs['position_company'])
        self._set_location_experience(vacancy_signs['location_experience'])
        self._set_salary(_SALARY_RANGE_PATTERN, _SALARY_PATTERN)
        self._set_url(_VACANCY_URL_PATTERN)
        self._set_subscription(vacancy_signs['splitter'])
        self._vacancy_html_parsing()

    def _set_position_company(self, splitter: str):
        parsing_str = self.text.split('\n')[0].strip(' *_')
        if splitter in parsing_str:
            self.position = parsing_str.split(splitter)[0].strip(' *_')
            self.company = parsing_str.split(splitter)[1].strip(' *_')
        else:
            self.position = parsing_str

    def _set_location_experience(self, pattern: list[str]):
        parsing_str = self.text.split('\n')[1].strip(' *_')
        matching = re.search(f'(.+), {_NUMERIC_PATTERN}?\s?({"|".join(pattern)})', parsing_str)
        if matching:
            if len(matching.groups()) in [2, 3]:
                self.location = matching.group(1)
            if len(matching.groups()) == 2 and matching.group(3)[0:1].isupper():
                self.experience = 0
            if len(matching.groups()) == 3:
                self.experience = str_to_numeric(matching.group(2))

    def _set_salary(self, range_pattern, salary_pattern):
        parsing_str = self.text.split('\n')[1].strip(' *_')
        matching = re.search(f'{range_pattern}\Z', parsing_str)
        if matching:
            if len(matching.groups()) == 2:
                self.min_salary = str_to_numeric(matching.group(1))
                self.max_salary = str_to_numeric(matching.group(2))
        matching = re.search(f'{salary_pattern}\Z', parsing_str)
        if matching:
            self.min_salary = str_to_numeric(matching.group(1))
            self.max_salary = self.min_salary

    def _set_url(self, pattern: str):
        matching = re.search(pattern, self.text)
        if matching:
            self.url = matching.group(0)

    def _set_subscription(self, pattern: list[str]):
        parsing_str = self.text.split('\n')[-1]
        matching = re.sub(f'{"|".join(pattern)}', '', parsing_str)
        if matching:
            self.subscription = matching.strip('\"\' *_`')

    def _vacancy_html_parsing(self):
        # Создаем объект BeautifulSoup для парсинга HTML-страницы с текстом вакансии
        soup = BeautifulSoup(self.raw_html, 'lxml')
        # Проверяем, не вернул ли сервер HTML-страницу с ошибкой
        if soup.find('h1'):
            # Получаем заголовок вакансии
            self.job_header = soup.find('h1').find('span').get_text().strip(' \n')
            # Получаем описание вакансии
            if soup.find('div', class_='mb-4 job-post__description'):
                self.job_description = soup.find('div', class_='mb-4 job-post__description').get_text()
            # Получаем дополнительную информацию о вакансии
            if soup.find('div', class_='card card-body'):
                job_card = soup.find('div', class_='card card-body')
                # Обрабатываем первый блок с дополнительной информацией о вакансии
                ul_tags = job_card.find_all('ul', class_='list-unstyled')
                if ul_tags and len(ul_tags) == 3:
                    # Обрабатываем первый блок с дополнительной информацией о вакансии
                    additional_info = []
                    li_tags = ul_tags[0].find_all('li')
                    for li_tag in li_tags:
                        additional_info.append(re.sub(r'\s+|\n', ' ', li_tag.get_text().strip()))
                    if len(additional_info) == 4:
                        self.requirements = '\n'.join(additional_info[0:1])
                        self.work_type = additional_info[2]
                        self.candidate_locations = additional_info[3].replace('Countries where we consider candidates',
                                                                              '').strip()
                    # Обрабатываем второй блок с дополнительной информацией о вакансии
                    additional_info.clear()
                    li_tags = ul_tags[1].find_all('li')
                    for li_tag in li_tags:
                        additional_info.append(re.sub(r'\s+|\n', ' ', li_tag.get_text().strip()))
                    self.main_tech = additional_info[0]
                    if len(additional_info) == 2:
                        self._tech_stack = additional_info[1]
                    # Обрабатываем третий блок с дополнительной информацией о вакансии
                    additional_info.clear()
                    li_tags = ul_tags[2].find_all('li')
                    for li_tag in li_tags:
                        additional_info.append(re.sub(r'\s+|\n', ' ', li_tag.get_text().strip()))
                        if len(additional_info) == 3:
                            self.domain = re.sub(r'Domain:', '', additional_info[0]).strip()
                            self.company_type = additional_info[1]
                            self.offices = re.sub('Office:', '', additional_info[2]).strip()


class StatisticMessage(Base):
    __tablename__ = _TABLE_NAMES['statistic_messages']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{_TABLE_NAMES['source_messages']}.message_id'))
    source_message: Mapped[SourceMessage] = relationship(back_populates='statistic_message')
    vacancies_in_30d: Mapped[int] = mapped_column(Integer, nullable=True)
    candidates_online: Mapped[int] = mapped_column(Integer, nullable=True)
    min_salary: Mapped[int] = mapped_column(Integer, nullable=True)
    max_salary: Mapped[int] = mapped_column(Integer, nullable=True)
    responses_to_vacancies: Mapped[int] = mapped_column(Integer, nullable=True)
    vacancies_per_week: Mapped[int] = mapped_column(Integer, nullable=True)
    candidates_per_week: Mapped[int] = mapped_column(Integer, nullable=True)
    parsing_status: Mapped[str]

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        statistic_signs = _DB_DATA['parsing_signs']['statistic']
        self._set_numeric_attr('vacancies_in_30d', statistic_signs['vacancies_in_30d'])
        self._set_numeric_attr('candidates_online', statistic_signs['candidates_online'])
        self._set_numeric_attr('responses_to_vacancies', statistic_signs['responses_to_vacancies'])
        self._set_numeric_attr('vacancies_per_week', statistic_signs['vacancies_per_week'])
        self._set_numeric_attr('candidates_per_week', statistic_signs['candidates_per_week'])
        self._set_salary(statistic_signs['salary'])
        self._set_parsing_status()

    def _set_numeric_attr(self, field_name: str, patterns: list):
        pattern = f"(?:({'|'.join(patterns)}):?\s+)({_NUMERIC_PATTERN})"
        match = re.search(pattern, self.source_message.text)
        if match and len(match.groups()) >= 2:
            setattr(self, field_name, str_to_numeric(match.group(2)))

    def _set_salary(self, patterns: list):
        pattern = f"(?:({'|'.join(patterns)}):?\s+){_SALARY_RANGE_PATTERN}"
        match = re.search(pattern, self.source_message.text)
        if match and len(match.groups()) >= 3:
            self.min_salary = str_to_numeric(match.group(2))
            self.max_salary = str_to_numeric(match.group(3))

    def _set_parsing_status(self):
        number_of_fields = 7
        success_count = sum(1 for x in (self.vacancies_in_30d, self.candidates_online, self.min_salary,
                                        self.max_salary, self.responses_to_vacancies, self.vacancies_per_week,
                                        self.candidates_per_week) if x is not None)
        self.parsing_status = 'OK' if success_count == number_of_fields else f'{success_count} / {number_of_fields}'


class ServiceMessage(Base):
    __tablename__ = _TABLE_NAMES['service_messages']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{_TABLE_NAMES['source_messages']}.message_id'))
    source_message: Mapped[SourceMessage] = relationship(back_populates='service_message')


# Создание соединения с базой данных и сессии
def connect_database():
    engine = create_engine('sqlite:///vacancies.db')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    return session()


# Загрузка шаблонов базы данных из файла
def read_db_data():
    global _DB_DATA
    with open('settings.json', 'r', encoding='utf-8') as file:
        _DB_DATA = json.load(file)
    return _DB_DATA


def get_db_data():
    return _DB_DATA


def get_vacancy_url_pattern():
    return _VACANCY_URL_PATTERN


def get_vacancy_pattern():
    return f'([\s\S]*?(?:{"|".join(_DB_DATA["parsing_signs"]["vacancy"]["splitter"])}).*)(?:\n\n)?'


def str_to_numeric(value: str | None) -> int | float | None:
    result = None
    if value is not None:
        try:
            if "." in value or "," in value:
                result = float(value.replace(",", "."))
            else:
                result = int(value)
        except (ValueError, AttributeError):
            pass
    if result is not None and not result % 1:
        result = int(result)
    return result


if __name__ == '__main__':
    pass

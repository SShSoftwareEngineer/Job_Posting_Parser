import json
import re
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, Integer, ForeignKey, Text, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

_DB_DATA = dict()
_DB_DATA_FILE = 'settings.json'
_NUMERIC_PATTERN = '[-+]?(?:\d+[.,]\d+|\d+|\.\d+)'
_SALARY_PATTERN = f'\$?({_NUMERIC_PATTERN})-({_NUMERIC_PATTERN})'
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
    message_type: Mapped[str]
    text: Mapped[str] = mapped_column(Text)
    vacancy_message: Mapped["VacancyMessage"] = relationship(back_populates="source_message")
    statistic_message: Mapped["StatisticMessage"] = relationship(back_populates="source_message")
    service_message: Mapped["ServiceMessage"] = relationship(back_populates="source_message")

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        self.message_type = self._set_message_type(_DB_DATA['message_type_patterns'])

    def _set_message_type(self, patterns: dict) -> str:
        result = ''
        for message_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if pattern in self.text:
                    result = message_type
        return result


class VacancyMessage(Base):
    __tablename__ = _TABLE_NAMES['vacancy_messages']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{_TABLE_NAMES['source_messages']}.message_id'))
    source_message: Mapped[SourceMessage] = relationship(back_populates='vacancy_message')
    position: Mapped[str] = mapped_column(String, nullable=True)
    company: Mapped[str] = mapped_column(String, nullable=True)
    location: Mapped[str] = mapped_column(String, nullable=True)
    experience: Mapped[str] = mapped_column(String, nullable=True)
    salary: Mapped[str] = mapped_column(String, nullable=True)
    url: Mapped[str] = mapped_column(String, nullable=True)
    subscription: Mapped[str] = mapped_column(String, nullable=True)
    header: Mapped[str] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)

    def __init__(self, **kw: Any):
        super().__init__(**kw)


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
        self.vacancies_in_30d = self._set_numeric_attr(statistic_signs['vacancies_in_30d'])
        self.candidates_online = self._set_numeric_attr(statistic_signs['candidates_online'])
        self.min_salary, self.max_salary = self._set_salary(statistic_signs['salary'])
        self.responses_to_vacancies = self._set_numeric_attr(statistic_signs['responses_to_vacancies'])
        self.vacancies_per_week = self._set_numeric_attr(statistic_signs['vacancies_per_week'])
        self.candidates_per_week = self._set_numeric_attr(statistic_signs['candidates_per_week'])
        self._set_parsing_status()

    def _set_numeric_attr(self, patterns: list) -> int | float:
        result = None
        pattern = f"(?:({'|'.join(patterns)}):?\s+)({_NUMERIC_PATTERN})"
        match = re.search(pattern, self.source_message.text)
        if match and len(match.groups()) >= 2:
            result = convert_str_to_numeric(match.group(2))
        return result

    def _set_salary(self, patterns: list) -> list[int | float]:
        min_salary, max_salary = None, None
        pattern = f"(?:({'|'.join(patterns)}):?\s+){_SALARY_PATTERN}"
        match = re.search(pattern, self.source_message.text)
        if match and len(match.groups()) >= 3:
            min_salary = convert_str_to_numeric(match.group(2))
            max_salary = convert_str_to_numeric(match.group(3))
        return [min_salary, max_salary]

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


def convert_str_to_numeric(value: str) -> int | float | None:
    result = None
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

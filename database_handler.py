import json
import re
from datetime import datetime
from typing import Optional, List, Any, Type

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, declared_attr

_DB_DATA = dict()
_DB_DATA_FILE = 'settings.json'
_NUMERIC_PATTERN = '[-+]?(?:\d+[.,]\d+|\d+|\.\d+)'


class Base(DeclarativeBase):
    pass


# Модель для архива исходных сообщений

class SourceMessage(Base):
    __tablename__ = 'source_msgs'
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, unique=True)
    date: Mapped[datetime]
    message_type: Mapped[str]
    text: Mapped[str] = mapped_column(Text)

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


class StatisticMessage(Base):
    __tablename__ = 'statistic_msgs'
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey('source_msgs.message_id'))
    source_message = relationship(SourceMessage)
    vacancies_in_30d: Mapped[int]
    candidates_online: Mapped[int]
    min_salary: Mapped[int]
    max_salary: Mapped[int]
    responses_to_vacancies: Mapped[int]
    vacancies_per_week: Mapped[int]
    candidates_per_week: Mapped[int]
    parsing_status: Mapped[str]

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        self.vacancies_in_30d = 0
        self.candidates_online = 0
        self.min_salary = 0
        self.max_salary = 0
        self.responses_to_vacancies = 0
        self.vacancies_per_week = 0
        self.candidates_per_week = 0

    def _set_vacancies_in_30d(self, patterns: dict) -> int:
        # ((?:Jobs|Вакансий):?\s+)([-+]?(?:\d+[.,]\d+|\d+|\.\d+))
        #      _NUMERIC_PATTERN = '[-+]?(?:\d+[.,]\d+|\d+|\.\d+)'
        ss = f"((?:{'|'.join(patterns)}):?\s+)({_NUMERIC_PATTERN})"
        sss = self.source_message.text
        match = re.search(ss, sss)
        return 1

    def _set_parsing_status(self):
        pass


class ServiceMessage(Base):
    __tablename__ = 'service_msgs'
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey('source_msgs.message_id'))
    source_message = relationship(SourceMessage)
    text: Mapped[str] = mapped_column(Text)

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        text = self.source_message.text


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


if __name__ == '__main__':
    pass

import re
import pandas as pd
from datetime import datetime
from typing import Any
from config_handler import *

from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Integer, ForeignKey, Text, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session


# Классы-модели сообщений SQLAlchemy

class Base(DeclarativeBase):
    pass


class SourceMessage(Base):
    __tablename__ = TABLE_NAMES['source']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, unique=True)
    date: Mapped[datetime]
    message_type: Mapped[str] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    vacancy: Mapped["VacancyMessage"] = relationship(back_populates="source")
    statistic: Mapped["StatisticMessage"] = relationship(back_populates="source")
    service: Mapped["ServiceMessage"] = relationship(back_populates="source")

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        self._set_message_type(config.message_signs)

    def _set_message_type(self, message_signs: dict):
        for message_type, patterns in message_signs.items():
            for pattern in patterns:
                if pattern in self.text:
                    self.message_type = message_type
                    return None


class VacancyMessage(Base):
    __tablename__ = TABLE_NAMES['vacancy']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TABLE_NAMES['source']}.message_id'))
    source: Mapped[SourceMessage] = relationship(back_populates='vacancy')
    # Параметры вакансии, получаемые из сообщения Telegram
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    t_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    t_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subscription: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Параметры вакансии, получаемые из по ссылке на сайт
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    h_position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lingvo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    h_experience: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    work_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    candidate_locations: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    main_tech: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tech_stack: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    offices: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    parsing_status: Mapped[str] = mapped_column(String, nullable=True)

    temp_count: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    temp_card: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        vacancy_text_signs = config.message_configs['vacancy'].text_parsing_signs
        vacancy_html_signs = config.message_configs['vacancy'].html_parsing_signs
        self._set_position_company(vacancy_text_signs.position_company)
        self._set_location_experience(vacancy_text_signs.location_experience)
        self._set_salary(config.re_patterns.salary_range, config.re_patterns.salary)
        self._set_url(config.get_url_pattern())
        self._set_subscription(vacancy_text_signs.subscription)
        self._vacancy_html_parsing(vacancy_html_signs)
        self._set_parsing_status()

    def _set_position_company(self, splitter: str):
        parsing_str = self.text.split('\n')[0].strip(' *_')
        if splitter in parsing_str:
            self.t_position = parsing_str.split(splitter)[0].strip(' *_')
            self.company = parsing_str.split(splitter)[1].strip(' *_')
        else:
            self.t_position = parsing_str

    def _set_location_experience(self, pattern: list[str]):
        parsing_str = self.text.split('\n')[1].strip(' *_')
        matching = re.search(f'(.+), {config.re_patterns.numeric}? ?({"|".join(pattern)})', parsing_str)
        if matching:
            if len(matching.groups()) in [2, 3]:
                self.location = matching.group(1)
            if len(matching.groups()) == 2 and matching.group(3)[0:1].isupper():
                self.t_experience = 0
            if len(matching.groups()) == 3:
                self.t_experience = str_to_numeric(matching.group(2))

    def _set_salary(self, range_pattern: str, salary_pattern: str):
        parsing_str = self.text.split('\n')[1].strip(' *_')
        matching = re.search(fr'{range_pattern}\Z', parsing_str)
        if matching:
            if len(matching.groups()) == 2:
                self.min_salary = str_to_numeric(matching.group(1))
                self.max_salary = str_to_numeric(matching.group(2))
        else:
            matching = re.search(fr'{salary_pattern}\Z', parsing_str)
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

    def _vacancy_html_parsing(self, patterns):
        # Проверяем, не вернул ли сервер HTML-страницу с ошибкой
        if re.search(r'Error \d{3}', self.raw_html) and len(self.raw_html) < 500:
            return None
        # Создаем объект BeautifulSoup для парсинга HTML-страницы с текстом вакансии
        soup = BeautifulSoup(self.raw_html, 'lxml')
        # Получаем заголовок вакансии
        if soup.find('h1').find('span'):
            self.h_position = html_to_text(str(soup.find('h1').find('span')))
        # Получаем описание вакансии
        if soup.find('div', class_=patterns.html_classes.description):
            self.description = html_to_text(str(soup.find('div', class_=patterns.html_classes.description)))
        # Получаем дополнительную информацию о вакансии из "карточки"
        if soup.find('div', class_=patterns.html_classes.job_card):
            job_card = soup.find('div', class_=patterns.html_classes.job_card)
            ul_tags = job_card.find_all('ul', class_=patterns.html_classes.ul_tags)

            self.temp_count = '_ ' if len(ul_tags) == 3 else f'{len(ul_tags)} '
            self.temp_card = ''

            self.note = None
            if ul_tags and len(ul_tags) == 3:
                # Обрабатываем первый блок: требования к английскому, опыт, тип работы, локации кандидатов
                additional_info = []
                li_tags = ul_tags[0].find_all('li')
                for li_tag in li_tags:
                    additional_info.append(html_to_text(str(li_tag)))
                if len(additional_info) in [4, 5]:
                    self.lingvo = additional_info[0]
                    self.h_experience = additional_info[1]
                    if len(additional_info) == 5:
                        self.note = additional_info[2] if self.note is None else f'{self.note}\n{additional_info[2]}'
                    self.work_type = additional_info[-2]
                    matching = re.search(f"(.+)\n({'|'.join(patterns.candidate_locations)})", additional_info[-1])
                    if matching:
                        self.candidate_locations = matching.group(1).strip()

                self.temp_count += '_ ' if len(additional_info) == 4 else f'{len(additional_info)} '
                self.temp_card += '\n'.join(additional_info) + '\n'

                # Обрабатываем второй блок: основная технология, технический стек
                additional_info.clear()
                li_tags = ul_tags[1].find_all('li')
                for li_tag in li_tags:
                    additional_info.append(html_to_text(str(li_tag)))
                self.main_tech = additional_info[0]
                if len(additional_info) == 2:
                    self.tech_stack = additional_info[1]

                self.temp_count += '_ ' if len(additional_info) in [1, 2] else f'{len(additional_info)} '
                self.temp_card += '\n'.join(additional_info) + '\n'

                # Обрабатываем третий блок: домен и тип компании, локация офисов
                additional_info.clear()
                li_tags = ul_tags[2].find_all('li')
                for li_tag in li_tags:
                    additional_info.append(html_to_text(str(li_tag)))
                if len(additional_info) in [2, 3, 4]:
                    if len(additional_info) == 4:
                        if re.search(f"{'|'.join(patterns.domain)}", additional_info[0]):
                            note_str = additional_info[3]
                        else:
                            note_str = additional_info[0]
                        self.note = note_str if self.note is None else f'{self.note}\n{note_str}'
                    pattern = ''.join([f"(?:{'|'.join(patterns.domain)}) +(?P<domain>.+)\n?",
                                       f"(?P<company_type>.+)?\n?",
                                       f"(?:{'|'.join(patterns.offices)} +(?P<offices>.+))?"])
                    matching = re.search(pattern, '\n'.join(additional_info))
                    if matching:
                        self.domain = matching.groupdict().get('domain')
                        self.company_type = matching.groupdict().get('company_type')
                        self.offices = matching.groupdict().get('offices')

                self.temp_count += '_ ' if len(additional_info) in [2, 3] else f'{len(additional_info)}'
                self.temp_card += '\n'.join(additional_info)
        self.raw_html = str(html_to_text(self.raw_html)[0:32767])

    def _set_parsing_status(self):
        pass


class StatisticMessage(Base):
    __tablename__ = TABLE_NAMES['statistic']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TABLE_NAMES['source']}.message_id'))
    source: Mapped[SourceMessage] = relationship(back_populates='statistic')
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
        statistic_signs = config.message_configs['statistic'].text_parsing_signs
        self._set_numeric_attr('vacancies_in_30d', statistic_signs.vacancies_in_30d)
        self._set_numeric_attr('candidates_online', statistic_signs.candidates_online)
        self._set_numeric_attr('responses_to_vacancies', statistic_signs.responses_to_vacancies)
        self._set_numeric_attr('vacancies_per_week', statistic_signs.vacancies_per_week)
        self._set_numeric_attr('candidates_per_week', statistic_signs.candidates_per_week)
        self._set_salary(statistic_signs.salary)
        self._set_parsing_status()

    def _set_numeric_attr(self, field_name: str, patterns: list):
        pattern = f"(?:({'|'.join(patterns)}):? +)({config.re_patterns.numeric})"
        match = re.search(pattern, self.source.text)
        if match and len(match.groups()) >= 2:
            setattr(self, field_name, str_to_numeric(match.group(2)))

    def _set_salary(self, patterns: list):
        pattern = f"(?:({'|'.join(patterns)}):? +){config.re_patterns.salary_range}"
        match = re.search(pattern, self.source.text)
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
    __tablename__ = TABLE_NAMES['service']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TABLE_NAMES['source']}.message_id'))
    source: Mapped[SourceMessage] = relationship(back_populates='service')


def export_data_to_excel():
    data_frames = dict()
    # Импортируем данные из каждой таблицы в соответствующий DataFrame
    # и устанавливаем имена столбцов для Excel
    for key in TABLE_NAMES.keys():
        data_frames[key] = pd.read_sql(config.export_to_excel[key].sql, engine.connect())
        data_frames[key].columns = config.export_to_excel[key].column_names
    # Записываем DataFrame(s) в соответствующие листы файла Excel
    with pd.ExcelWriter('result.xlsx', engine="openpyxl") as writer:
        for key in TABLE_NAMES.keys():
            data_frames[key].to_excel(writer, sheet_name=config.export_to_excel[key].sheet_name,
                                      index=False, header=True, freeze_panes=(1, 1))


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


def html_to_text(html: str) -> str:
    # Заменяем последовательности '\n' на пробелы
    text = re.sub(r'\n+', ' ', html)
    # Заменяем теги <p>, <div> на '\n'
    text = re.sub(r'</?(p|div)[^>]*>', '\n', text)
    # Заменяем <br> на '\n'
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Удаляем все оставшиеся HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    # Убираем лишние пробелы и пустые строки
    text = re.sub(r'\n+', '\n', text).strip()
    # Убираем лишние пробелы в начале и конце каждой строки
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
    # Убираем лишние пробелы в строках
    text = re.sub(r' +', ' ', text)
    return text


# Подключение к базе данных
# Создание соединения с базой данных и сессии
engine = create_engine('sqlite:///vacancies.db')
session = Session(engine)
Base.metadata.create_all(engine)

if __name__ == '__main__':
    pass

"""
The module contains model classes, functions, and constants for working with an SQLite database using SQLAlchemy.

HTTP_ERRORS: a dictionary containing descriptions of HTTP request errors
class Base(DeclarativeBase): a declarative class for creating tables in the database
class RawMessage(Base): a model class for original Telegram messages
class VacancyMessage(Base): a model class for vacancy messages
class StatisticMessage(Base): a model class for statistics messages
class ServiceMessage(Base): a model class for service messages
VacancyWeb(Base): a model class for job vacancy URLs on the website
MessageSource(Base): a model class for message sources
MessageType(Base): a model class for message types
def export_data_to_excel(): a function for exporting data from the database to MS Excel file
session: a session object for working with the database
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Type, TypeVar, List
import pandas as pd
from sqlalchemy import create_engine, Integer, ForeignKey, Text, String, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from config_handler import config
from configs.config import GlobalConst, TableNames, MessageSources, MessageTypes

# A dictionary containing descriptions of HTTP request errors / Описание ошибок HTTP-запросов
HTTP_ERRORS = {
    403: 'Error 403 Forbidden',
    404: 'Error 404 Not Found',
    429: 'Error 429 Too Many Requests',
    "IP blocked": "Error 403 Forbidden or 429 Too Many Requests"
}


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """ A declarative class for creating tables in the database """


class RawMessage(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for original Telegram messages
    Класс-модель для исходных сообщений Telegram
    Attributes:
        id (Mapped[int]): database record ID
        message_id (Mapped[int]): Telegram message ID
        email_uid (Mapped[int]): Email message UID
        date (Mapped[datetime]): message date
        text (Mapped[str]): message text
    """
    __tablename__ = TableNames.raw_message.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[datetime]
    message_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    email_uid: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    # Relationships to 'vacancy' table
    vacancy: Mapped[List['Vacancy']] = relationship(back_populates='raw_message', cascade='all, delete-orphan')
    # Relationships to 'statistics' table
    statistic: Mapped['Statistic'] = relationship(back_populates='raw_message', uselist=False,
                                                  cascade='all, delete-orphan')
    # Relationships to 'service' table
    service: Mapped['Service'] = relationship(back_populates='raw_message', uselist=False, cascade='all, delete-orphan')
    # Relationships to 'message_sources' table
    message_source_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.message_source.value}.id'),
                                                   index=True)
    message_source: Mapped['MessageSource'] = relationship(back_populates='raw_message')
    # Relationships to 'message_types' table
    message_type_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.message_type.value}.id'),
                                                 index=True)
    message_type: Mapped['MessageType'] = relationship(back_populates='raw_message')

    # def __init__(self, **kw: Any):
    #     """
    #     Initialization of the RawMessage object. Determining the message type based on its content
    #     Инициализация объекта RawMessage. Определение типа сообщения по содержимому
    #     """
    #     super().__init__(**kw)
    #     # self._set_message_type(config.tg_message_signs)

    # def _set_message_type(self, tg_message_signs: dict):
    #     """
    #     Determining the message type based on its content
    #     Определяет тип сообщения по содержимому
    #     """
    #     for message_type, patterns in tg_message_signs.items():
    #         matching = re.search(f"{'|'.join(patterns)}", self.text)
    #         if matching:
    #             self.message_type = message_type
    #             return


class Vacancy(Base):  # pylint: disable=too-few-public-methods, disable=too-many-instance-attributes
    """
    A model class for vacancy messages

    Класс-модель для сообщений о вакансиях

    Attributes:
    id (Mapped[int]): database record ID
    message_id (Mapped[int]): Telegram message ID
    source (Mapped[RawMessage]): link to the original message
    position_msg (Mapped[str]): position, job title
    position_web (Mapped[str]): position, job title on the website
    location (Mapped[str]): company location
    domain (Mapped[str]): company domain
    experience_msg (Mapped[int]): work experience requirements
    experience_web (Mapped[str]): work experience requirements on the website
    main_tech (Mapped[str]): the main technology of the project
    tech_stack (Mapped[str]): technology stack
    lingvo (Mapped[str]): english language requirements
    work_type (Mapped[str]): work type (office, remote etc.)
    candidate_locations (Mapped[str]): candidate locations under consideration
    min_salary (Mapped[int]): minimum salary
    max_salary (Mapped[int]): maximum salary
    description (Mapped[str]): vacancy description on the website
    company (Mapped[str]): company
    company_type (Mapped[str]): company type (outsource, outstaff, product etc.)
    offices (Mapped[str]): company offices locations
    text (Mapped[str]): message text
    subscription (Mapped[str]): subscription to job vacancy messages
    notes (Mapped[str]): notes
    """
    __tablename__ = TableNames.vacancy.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    position_msg: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    position_web: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    experience_msg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    experience_web: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    main_tech: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tech_stack: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lingvo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    work_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    candidate_locations: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    min_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    offices: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subscription: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    text_data_hash: Mapped[str] = mapped_column(String)
    # Service parameters used for parsing debugging / Служебные параметры, используемые при отладке парсинга
    parsing_status: Mapped[str] = mapped_column(String, nullable=True)
    temp_card: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Relationships to 'raw_messages' table
    raw_message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.raw_message.value}.id'), index=True,
                                                nullable=True)
    raw_message: Mapped['RawMessage'] = relationship(back_populates='vacancy')
    # Relationships to 'vacancies_web' table
    vacancy_web: Mapped[List['VacancyWeb']] = relationship(back_populates='vacancy', cascade='all, delete-orphan')

    # def __init__(self, **kw: Any):
    #     """
    #     Initialization of the VacancyMessage object. Parsing the message text and HTML code of the job vacancy page
    #     Инициализация объекта VacancyMessage. Парсинг текста сообщения и HTML-кода страницы вакансии
    #     """
    #     super().__init__(**kw)
    #     vacancy_text_signs = config.message_configs.vacancy.text_parsing_signs
    #     vacancy_html_signs = config.message_configs.vacancy.html_parsing_signs
    #     # Extracting the position and company name from the Telegram message text
    #     # Извлечение позиции, названия компании из текста сообщения Telegram
    #     self._set_position_company(vacancy_text_signs["position_company"])
    #     # Extracting the company location and experience requirements from the Telegram message text
    #     # Извлечение локации компании, опыта работы из текста сообщения Telegram
    #     self._set_location_experience(vacancy_text_signs["location_experience"])
    #     # Extracting salary information from the Telegram message text
    #     # Извлечение информации о зарплате из текста сообщения Telegram
    #     self._set_salary(config.re_patterns.salary_range, config.re_patterns.salary)
    #     # Extracting full vacancy text URL on the website from the Telegram message text
    #     # Извлечение URL вакансии на сайте из текста сообщения Telegram
    #     self._set_url(config.get_url_pattern())
    #     # Extracting subscription to job vacancy messages from the Telegram message text
    #     # Извлечение информации о подписке рассылки из текста сообщения Telegram
    #     self._set_subscription(vacancy_text_signs["subscription"])
    #     # Parsing job posting information from the HTML code of the job posting page on the website
    #     # Парсинг информации о вакансии из HTML-кода страницы вакансии на сайте
    #     self._vacancy_html_parsing(vacancy_html_signs)
    #     for key, value in vars(self).items():
    #         if value == "":
    #             setattr(self, key, None)
    #     # Validating the parsing results of all fields and setting the job vacancy parsing status
    #     # Проверка результатов парсинга всех полей и установка статуса парсинга вакансии
    #     self._set_parsing_status()

    # def _set_position_company(self, splitter: list[str]):
    #     """
    #     Extracting the position and company name from the Telegram message text
    #     Извлечение позиции, названия компании из текста сообщения Telegram
    #     """
    #     parsing_str = re.sub(r'[*_`]+', '', str(self.text).split('\n', maxsplit=1)[0]).replace('  ', ' ')
    #     matching = re.split(f"{'|'.join(splitter)}", parsing_str)
    #     if matching:
    #         self.position_msg = matching[0]
    #         if len(matching) > 1:
    #             self.company = matching[1]
    #     else:
    #         self.position_msg = parsing_str
    #
    # def _set_location_experience(self, pattern: list[str]):
    #     """
    #     Extracting the company location and experience requirements from the Telegram message text
    #     Извлечение локации компании, требований к опыту работы из текста сообщения Telegram
    #     """
    #     parsing_str = re.sub(r'[*_`]+', '', str(self.text).split('\n')[1]).replace('  ', ' ')
    #     matching = re.search(f'(.+), {config.re_patterns.numeric}? ?({"|".join(pattern)})', parsing_str)
    #     if matching:
    #         self.location = matching.group(1)
    #         self.experience_msg = cast(int | None, str_to_numeric(matching.group(2)))
    #         if matching.group(2) is None and matching.group(3) is not None:
    #             self.experience_msg = 0
    #
    # def _set_salary(self, range_pattern: str, salary_pattern: str):
    #     """
    #     Extracting salary information from the Telegram message text
    #     Извлечение информации о зарплате из текста сообщения Telegram
    #     """
    #     parsing_str = re.sub(r'[*_`]+', '', str(self.text).split('\n')[1]).replace('  ', ' ')
    #     matching = re.search(fr'{range_pattern}\Z', parsing_str)
    #     if matching:
    #         if len(matching.groups()) == 2:
    #             self.min_salary = cast(int | None, str_to_numeric(matching.group(1)))
    #             self.max_salary = cast(int | None, str_to_numeric(matching.group(2)))
    #     else:
    #         matching = re.search(fr'{salary_pattern}\Z', parsing_str)
    #         if matching:
    #             self.min_salary = cast(int | None, str_to_numeric(matching.group(1)))
    #             self.max_salary = self.min_salary
    #
    # def _set_url(self, pattern: str):
    #     """
    #     Extracting full vacancy text URL on the website from the Telegram message text
    #     Извлечение URL вакансии на сайте из текста сообщения Telegram
    #     """
    #     matching = re.search(pattern, str(self.text))
    #     if matching:
    #         self.url = matching.group(0)
    #
    # def _set_subscription(self, pattern: list[str]):
    #     """
    #     Extracting subscription to job vacancy messages from the Telegram message text
    #     Извлечение информации о подписке рассылки из текста сообщения Telegram
    #     """
    #     parsing_str = re.sub(r'[*_`]+', '', str(self.text).rsplit('\n', maxsplit=1)[-1]).replace('  ', ' ')
    #     matching = re.sub(f'{"|".join(pattern)}', '', parsing_str)
    #     if matching:
    #         self.subscription = matching.strip('\"\' *_`')
    #
    # def _is_vacancy_html_error(self) -> bool:
    #     """
    #     Checking whether the server returned an HTML page with an error
    #     Проверка, не вернул ли сервер HTML-страницу с ошибкой
    #     """
    #     if self.vacancy_web.raw_html is None:
    #         return False
    #     matching = re.search(r'Error \d{3}', self.vacancy_web.raw_html)
    #     if matching and matching.start(0) < 500:
    #         return True
    #     return False
    #
    # def _safety_add_string(self, field: str, adding_string: str):
    #     """
    #     Adds a line to the field if it is not empty; otherwise, assigns the value to the field.
    #     Добавление строки в поле, если оно не пустое; иначе присваивает значение полю
    #     """
    #     if not adding_string:
    #         return
    #     if getattr(self, field) is None:
    #         setattr(self, field, adding_string.strip())
    #     else:
    #         if adding_string not in getattr(self, field):
    #             setattr(self, field, f'{getattr(self, field)}\n{adding_string.strip()}')
    #
    # def _vacancy_html_parsing(self, patterns):  # pylint: disable=too-many-branches, disable=too-many-statements
    #     """
    #     Parsing job posting information from the HTML code of the job posting page on the website
    #     Парсинг информации о вакансии из HTML-кода страницы вакансии на сайте
    #     """
    #     # Checking that the server returned an HTML page with the vacancy text
    #     # Проверяем, что сервер вернул HTML-страницу с текстом вакансии
    #     if self._is_vacancy_html_error():
    #         return
    #     # Create a BeautifulSoup object for parsing the HTML page with the job posting text
    #     # Создаем объект BeautifulSoup для парсинга HTML-страницы с текстом вакансии
    #     soup = BeautifulSoup(self.vacancy_web.raw_html, 'lxml')
    #     # Retrieving the job title
    #     # Получаем заголовок вакансии
    #     if soup.find('h1').find('span'):
    #         self.position_web = html_to_text(str(soup.find('h1').find('span')))
    #     # Retrieving the job description
    #     # Получаем описание вакансии
    #     if soup.find('div', class_=patterns.html_classes.description):
    #         self.description = html_to_text(str(soup.find('div', class_=patterns.html_classes.description)))
    #     # Retrieving additional job information from the "job card."
    #     # Получаем дополнительную информацию о вакансии из "карточки вакансии"
    #     if soup.find('div', class_=patterns.html_classes.job_card):
    #         job_card = soup.find('div', class_=patterns.html_classes.job_card)
    #         ul_tags = job_card.find_all('ul', class_=patterns.html_classes.ul_tags)
    #
    #         self.temp_card = None
    #
    #         self.notes = None
    #         if ul_tags and len(ul_tags) == 3:
    #             additional_info = []
    #             # Parsing the first block: English requirements, experience, work type, and candidate locations
    #             # Парсим первый блок: требования к английскому, опыту, тип работы, локации кандидатов
    #             li_tags = ul_tags[0].find_all('li')
    #             for li_tag in li_tags:
    #                 additional_info.append(html_to_text(str(li_tag)))
    #
    #             self._safety_add_string('temp_card', '\n'.join([x for x in additional_info if x]))
    #
    #             for i, add_info in enumerate(additional_info):
    #                 if re.search(f"{'|'.join(patterns.lingvo)}", add_info):
    #                     self._safety_add_string('lingvo', add_info)
    #                     additional_info[i] = ''
    #                 if re.search(f"{'|'.join(patterns.experience)}", add_info):
    #                     self.experience_web = add_info
    #                     additional_info[i] = ''
    #                 if re.search(f"{'|'.join(patterns.work_type)}", add_info):
    #                     self.work_type = add_info
    #                     additional_info[i] = ''
    #                 if re.search(f"{'|'.join(patterns.candidate_locations)}", add_info):
    #                     self.candidate_locations = add_info.split('\n')[0]
    #                     additional_info[i] = ''
    #             self._safety_add_string('notes', '\n'.join([x for x in additional_info if x]))
    #             # Parsing the second block: main technology and tech stack.
    #             # Парсим второй блок: основная технология, технический стек
    #             additional_info.clear()
    #             li_tags = ul_tags[1].find_all('li')
    #             for li_tag in li_tags:
    #                 additional_info.append(html_to_text(str(li_tag)))
    #
    #             self._safety_add_string('temp_card', '\n'.join([x for x in additional_info if x]))
    #
    #             self.main_tech = additional_info[0]
    #             if len(additional_info) == 2:
    #                 self.tech_stack = additional_info[1]
    #             # Parsing the third block: company domain and company type, office locations.
    #             # Парсим третий блок: домен и тип компании, локация офисов
    #             additional_info.clear()
    #             li_tags = ul_tags[2].find_all('li')
    #             for li_tag in li_tags:
    #                 additional_info.append(html_to_text(str(li_tag)))
    #
    #             self._safety_add_string('temp_card', '\n'.join([x for x in additional_info if x]))
    #
    #             for i, add_info in enumerate(additional_info):
    #                 if re.search(f"{'|'.join(patterns.domain)}", add_info):
    #                     self.domain = re.sub(f"{'|'.join(patterns.domain)}", '', add_info).strip()
    #                     additional_info[i] = ''
    #                 if re.search(f"{'|'.join(patterns.offices)}", add_info):
    #                     self.offices = re.sub(f"{'|'.join(patterns.offices)}", '', add_info).strip()
    #                     additional_info[i] = ''
    #                 if re.search(f"{'|'.join(patterns.company_type)}", add_info):
    #                     self.company_type = add_info
    #                     additional_info[i] = ''
    #             self._safety_add_string('notes', '\n'.join([x for x in additional_info if x]))
    #
    # def _set_parsing_status(self):
    #     """
    #     Validating the parsing results of all fields and setting the job vacancy parsing status
    #     Проверка результатов парсинга всех полей и установка статуса парсинга вакансии
    #     """
    #     # Validating the parsing results for the Telegram message text fields
    #     # Проверка результатов парсинга полей текста сообщения Telegram
    #     counted_text_fields = [self.position_msg, self.company, self.location, self.experience_msg,
    #                            self.url, self.subscription]
    #     parsing_text_status = 'OK '
    #     none_count = sum(1 for item in counted_text_fields if item is None)
    #     if none_count:
    #         parsing_text_status = f'{len(counted_text_fields) - none_count} / {len(counted_text_fields)}'
    #     # Validating the parsing results for the fields from the HTML code of the job vacancy page on the website
    #     # Проверка результатов парсинга полей из HTML-кода страницы вакансии на сайте
    #     counted_html_fields = [self.position_web, self.description, self.lingvo, self.experience_web,
    #                            self.work_type, self.candidate_locations, self.main_tech, self.tech_stack,
    #                            self.domain, self.company_type]
    #     parsing_html_status = 'OK'
    #     if not self._is_vacancy_html_error():
    #         none_count = sum(1 for item in counted_html_fields if item is None)
    #         if none_count:
    #             parsing_html_status = f'{len(counted_html_fields) - none_count} / {len(counted_html_fields)}'
    #     self.parsing_status = f'{parsing_text_status} _ {parsing_html_status}'


class Statistic(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for statistics messages

    Класс-модель для сообщений со статистикой

    Attributes:
    id (Mapped[int]): database record ID
    message_id (Mapped[int]): Telegram message ID
    source (Mapped[RawMessage]): link to the original message
    vacancies_in_30d (Mapped[int]): number of job vacancies in the last 30 days
    candidates_online (Mapped[int]): number of candidates online
    min_salary (Mapped[int]): minimum salary
    max_salary (Mapped[int]): maximum salary
    responses_to_vacancies (Mapped[int]): number of responses per vacancy
    vacancies_per_week (Mapped[int]): number of job vacancies in the last week
    candidates_per_week (Mapped[int]): number of candidates in the last week
    """
    __tablename__ = TableNames.statistic.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vacancies_in_30d: Mapped[int] = mapped_column(Integer, nullable=True)
    candidates_online: Mapped[int] = mapped_column(Integer, nullable=True)
    min_salary: Mapped[int] = mapped_column(Integer, nullable=True)
    max_salary: Mapped[int] = mapped_column(Integer, nullable=True)
    responses_to_vacancies: Mapped[int] = mapped_column(Integer, nullable=True)
    vacancies_per_week: Mapped[int] = mapped_column(Integer, nullable=True)
    candidates_per_week: Mapped[int] = mapped_column(Integer, nullable=True)
    parsing_status: Mapped[str] = mapped_column(Integer, nullable=True)
    # Relationships to 'RawMessage' table
    raw_message_id: Mapped[int] = mapped_column(Integer,
                                                ForeignKey(f'{TableNames.raw_message.value}.id', ondelete='CASCADE'),
                                                index=True, unique=True)
    raw_message: Mapped['RawMessage'] = relationship(back_populates='statistic')

    # def __init__(self, **kw: Any):
    #     """
    #     Initialization of the StatisticMessage object. Parsing message text with statistics
    #     Инициализация объекта StatisticMessage. Парсинг текста сообщения со статистикой
    #     """
    #     super().__init__(**kw)
    #     statistic_signs = config.message_configs.statistics.text_parsing_signs
    #     # Extracting numerical values from the Telegram message text
    #     # Извлечение числовых значений из текста сообщения Telegram
    #     self._set_numeric_attr('vacancies_in_30d', statistic_signs["vacancies_in_30d"])
    #     self._set_numeric_attr('candidates_online', statistic_signs["candidates_online"])
    #     self._set_numeric_attr('responses_to_vacancies', statistic_signs["responses_to_vacancies"])
    #     self._set_numeric_attr('vacancies_per_week', statistic_signs["vacancies_per_week"])
    #     self._set_numeric_attr('candidates_per_week', statistic_signs["candidates_per_week"])
    #     # Extracting salary information from the Telegram message text
    #     # Извлечение информации о зарплате из текста сообщения Telegram
    #     self._set_salary(statistic_signs["salary"])
    #     for key, value in vars(self).items():
    #         if value == "":
    #             setattr(self, key, None)
    #     # Validating the parsing results of all fields and setting the statistics parsing status
    #     # Проверка результатов парсинга всех полей и установка статуса парсинга статистики
    #     self._set_parsing_status()
    #
    # def _set_numeric_attr(self, field_name: str, patterns: list):
    #     """
    #     Extracting numerical values from the Telegram message text
    #     Извлечение числового значения из текста сообщения Telegram
    #     """
    #     if getattr(self, field_name) is not None:
    #         return
    #     pattern = f"(?:({'|'.join(patterns)}):? +)({config.re_patterns.numeric})"
    #     match = re.search(pattern, self.raw_message.text)
    #     if match and len(match.groups()) >= 2:
    #         setattr(self, field_name, str_to_numeric(match.group(2)))
    #
    # def _set_salary(self, patterns: list):
    #     """
    #     Extracting salary information from the Telegram message text
    #     Извлечение информации о зарплате из текста сообщения Telegram
    #     """
    #     pattern = f"(?:({'|'.join(patterns)}):? +){config.re_patterns.salary_range}"
    #     match = re.search(pattern, self.raw_message.text)
    #     if match and len(match.groups()) >= 3:
    #         self.min_salary = cast(int, str_to_numeric(match.group(2)))
    #         self.max_salary = cast(int, str_to_numeric(match.group(3)))
    #
    # def _set_parsing_status(self):
    #     """
    #     Validating the parsing results of all fields and setting the statistics parsing status
    #     Проверка результатов парсинга всех полей и установка статуса парсинга статистики
    #     """
    #     counted_fields = [self.vacancies_in_30d, self.candidates_online, self.min_salary, self.max_salary,
    #                       self.responses_to_vacancies, self.vacancies_per_week, self.candidates_per_week]
    #     none_count = sum(1 for item in counted_fields if item is None)
    #     if none_count:
    #         self.parsing_status = f'{len(counted_fields) - none_count} / {len(counted_fields)}'
    #     else:
    #         self.parsing_status = 'OK'


class Service(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for service messages

    Класс-модель для служебных сообщений

    Attributes:
    id (Mapped[int]): database record ID
    message_id (Mapped[int]): Telegram message ID
    source (Mapped[RawMessage]): link to the original message
    """
    __tablename__ = TableNames.service.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Relationships to 'RawMessage' table
    raw_message_id: Mapped[int] = mapped_column(Integer,
                                                ForeignKey(f'{TableNames.raw_message.value}.id', ondelete='CASCADE'),
                                                index=True, unique=True)
    raw_message: Mapped['RawMessage'] = relationship(back_populates='service')


class VacancyWeb(Base):
    """
    Class model for job vacancy URLs on the website
    Класс-модель для URL-адресов вакансий на сайте
    """
    __tablename__ = TableNames.vacancy_web.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_check: Mapped[Optional[datetime]]
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    # Relationships to 'vacancies' table
    vacancy_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.vacancy.value}.id', ondelete='CASCADE'),
                                            nullable=True)
    vacancy: Mapped['Vacancy'] = relationship(back_populates='vacancy_web')


class MessageSource(Base):
    """
    A model class for message sources
    Класс-модель для источников сообщений
    """
    __tablename__ = TableNames.message_source.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Relationships to 'raw_messages' table
    raw_message: Mapped[List['RawMessage']] = relationship(back_populates='message_source')


class MessageType(Base):
    """
    A model class for message types
    Класс-модель для типов сообщений
    """
    __tablename__ = TableNames.message_type.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Relationships to 'raw_messages' table
    raw_message: Mapped[List['RawMessage']] = relationship(back_populates='message_type')


# TypeVar for model classes, bound to Base
ModelType = TypeVar('ModelType', bound=Base)


class DatabaseHandler:
    """
    A class to represent handle database operations.
    Класс для представления операций с базой данных.
    """

    def upsert_record(self, model_class: Type[ModelType],
                      filter_fields: dict[str, Any],
                      update_fields: dict[str, Any]) -> tuple[ModelType, bool]:
        """
        Universal function for searching and updating/creating records in any database model
        Универсальная функция для поиска и обновления/создания записи в любой модели БД
        Attributes:
            model_class (Type[ModelType]): model class in which to search/create a record
            filter_fields (dict[str, Any]): fields for searching the record
            update_fields (dict[str, Any]): fields for updating/creating the record
        Returns:
            ModelType: the found or created/updated record
        """

        # Checking the record for existence / Проверяем запись на существование
        existing = self.session.query(model_class).filter_by(**filter_fields).first()
        if filter_fields and existing:
            # Updating an existing record / Обновляем существующую запись
            for key, value in update_fields.items():
                setattr(existing, key, value)
            added = False
        else:
            # Create a new record / Создаем новую запись
            existing = model_class(**{**filter_fields, **update_fields})
            self.session.add(existing)
            self.session.flush()  # Flush to get the ID if it's an autoincrement field
            added = True
        return existing, added

    def setup_database_connection(self):
        """
        Настройка параметров подключения к базе данных SQLite
        """

        # Enforce foreign key constraints in SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _):  # _ используется вместо необязательного параметра connection_record
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    def __init__(self):
        """
        Initializes the database handler by creating an engine, a session, and the necessary tables.
        Инициализирует обработчик базы данных, создавая движок, сессию и необходимые таблицы.
        """
        # Connecting to the database. Creating a database connection and session
        # Подключение к базе данных. Создаем соединение с базой данных и сессию
        self.engine = create_engine(f'sqlite:///{GlobalConst.database_file}')
        self.setup_database_connection()
        self.session = Session(self.engine)
        # Creating tables in the database if they do not exist
        # Создаем таблицы в базе данных, если они отсутствуют
        Base.metadata.create_all(self.engine)
        # Проверяем наличие данных в статической таблице с источниками сообщений и добавляем их при необходимости
        for message_source in MessageSources:
            self.upsert_record(MessageSource, dict(id=message_source.value),
                               dict(name=message_source.name))
        # Проверяем наличие данных в статической таблице с типами сообщений и добавляем их при необходимости
        for message_type in MessageTypes:
            self.upsert_record(MessageType, dict(id=message_type.type_id),
                               dict(name=message_type.name))
        self.session.commit()

    def export_data_to_excel(self):
        """
        Exporting data from the database to an MS Excel file
        Экспорт данных из БД в файл формата MS Excel
        """
        data_frames = {}
        # Импортируем данные из каждой таблицы в соответствующий DataFrame
        # и устанавливаем имена столбцов для Excel
        for table in TableNames.get_table_names():
            data_frames[table] = pd.read_sql(config.export_to_excel[table].sql, self.engine.connect())
            data_frames[table].columns = config.export_to_excel[table].columns.values()
        # Determining the available Excel file name for export
        # Определяем доступное имя Excel файла для экспорта
        excel_file_suffix = 1
        excel_file_name = Path(GlobalConst.excel_file)
        while excel_file_name.exists():
            excel_file_name = Path(excel_file_name.as_posix().replace('.xlsx', f'({excel_file_suffix}).xlsx'))
            excel_file_suffix += 1
        # Writing DataFrame(s) to the corresponding sheets of the Excel file
        # Записываем DataFrame(s) в соответствующие листы файла Excel
        with pd.ExcelWriter(excel_file_name, engine="openpyxl") as writer:
            for table in TableNames.get_table_names():
                data_frames[table].to_excel(writer, sheet_name=config.export_to_excel[table].sheet_name,
                                            index=False, header=True, freeze_panes=(1, 1))


# Создаем экземпляр DatabaseHandler()
db_handler = DatabaseHandler()

if __name__ == '__main__':
    pass

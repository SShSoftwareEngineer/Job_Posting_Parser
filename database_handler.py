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
from sqlalchemy import create_engine, Integer, ForeignKey, Text, String, event, Engine, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from config_handler import config
from configs.config import GlobalConst, TableNames, MessageSources, MessageTypes, VacancyAttrs

# A dictionary containing descriptions of HTTP request errors / Описание ошибок HTTP-запросов
HTTP_ERRORS = {
    403: 'Error 403 Forbidden',
    404: 'Error 404 Not Found',
    429: 'Error 429 Too Many Requests',
    "IP blocked": "Error 403 Forbidden or 429 Too Many Requests"
}


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """ A declarative class for creating tables in the database """


# Table implementing a many-to-many relationship between the Vacancy and VacancyData tables
# Таблица, реализующая отношение «многие-ко-многим» к таблицам «Vacancy» и «VacancyData»
vacancy_vacancy_data_links = Table(
    TableNames.VACANCY_DATA_VACANCIES_LINKS.value, Base.metadata,
    Column('vacancy_id', String,
           ForeignKey(f'{TableNames.VACANCIES.value}.id'), primary_key=True, index=True),
    Column('vacancy_data_id', Integer,
           ForeignKey(f'{TableNames.VACANCY_DATA.value}.id'), primary_key=True, index=True)
)


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

    __tablename__ = TableNames.RAW_MESSAGES.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[datetime]
    message_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    email_uid: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    html: Mapped[str] = mapped_column(Text, nullable=True)
    parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    # Relationships to 'Vacancy' table
    vacancy: Mapped[List['Vacancy']] = relationship(back_populates='raw_message', cascade='all, delete-orphan')
    # Relationships to 'Statistic' table
    statistic: Mapped['Statistic'] = relationship(back_populates='raw_message', uselist=False,
                                                  cascade='all, delete-orphan')
    # Relationships to 'Service' table
    service: Mapped['Service'] = relationship(back_populates='raw_message', uselist=False, cascade='all, delete-orphan')
    # Relationships to 'MessageSource' table
    message_source_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.MESSAGE_SOURCE.value}.id'),
                                                   index=True)
    message_source: Mapped['MessageSource'] = relationship(back_populates='raw_message')
    # Relationships to 'MessageType' table
    message_type_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.MESSAGE_TYPE.value}.id'),
                                                 index=True)
    message_type: Mapped['MessageType'] = relationship(back_populates='raw_message')


class VacancyData(Base):
    """
    A model class for vacancies data
    Класс-модель для параметров вакансий
    """

    __tablename__ = TableNames.VACANCY_DATA.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    attr_value: Mapped[str] = mapped_column(String, nullable=False)
    # Relationships to 'VacancyAttribute' table
    attr_name_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.VACANCY_ATTRS.value}.id'), index=True)
    attr_name: Mapped['VacancyAttribute'] = relationship(back_populates='vacancy_attr')
    # Relationships to 'Vacancy' table, many-to-many
    vacancy: Mapped[List['Vacancy']] = relationship(secondary=vacancy_vacancy_data_links, back_populates='vacancy_data')


class Vacancy(Base):
    """
    A model class for vacancy messages
    Класс-модель для сообщений о вакансиях
    Attributes:
        id (Mapped[int]): database record ID
        source (Mapped[RawMessage]): link to the original message
        domain (Mapped[str]): company domain
        main_tech (Mapped[str]): the main technology of the project
        tech_stack (Mapped[str]): technology stack
        lingvo (Mapped[str]): english language requirements
        work_type (Mapped[str]): work type (office, remote etc.)
        candidate_locations (Mapped[str]): candidate locations under consideration
        company_type (Mapped[str]): company type (outsource, outstaff, product etc.)
        offices (Mapped[str]): company offices locations
        notes (Mapped[str]): notes
    """

    __tablename__ = TableNames.VACANCIES.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Hash параметров как идентификатор вакансии
    data_hash: Mapped[str] = mapped_column(String, nullable=True)
    # Service parameters used for parsing debugging / Служебные параметры, используемые при отладке парсинга
    text_parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    email_parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    html_parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    temp_card: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Relationships to 'RawMessage' table
    raw_message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.RAW_MESSAGES.value}.id'), index=True,
                                                nullable=True)
    raw_message: Mapped['RawMessage'] = relationship(back_populates='vacancy')
    # Relationships to 'VacancyWeb' table
    vacancy_web: Mapped[List['VacancyWeb']] = relationship(back_populates='vacancy', cascade='all, delete-orphan')
    # Relationships to 'VacancyData' table, many-to-many
    vacancy_data: Mapped[List['VacancyData']] = relationship(secondary=vacancy_vacancy_data_links,
                                                             back_populates='vacancy')

    # def __init__(self, **kw: Any):
    #     """
    #     Initialization of the VacancyMessage object. Parsing the message text and HTML code of the job vacancy page
    #     Инициализация объекта VacancyMessage. Парсинг текста сообщения и HTML-кода страницы вакансии
    #     """
    #     super().__init__(**kw)
    #     vacancy_text_signs = config.message_configs.vacancy.text_parsing_signs
    #     vacancy_html_signs = config.message_configs.vacancy.html_parsing_signs

    #     # Parsing job posting information from the HTML code of the job posting page on the website
    #     # Парсинг информации о вакансии из HTML-кода страницы вакансии на сайте
    #     self._vacancy_html_parsing(vacancy_html_signs)
    #     for key, value in vars(self).items():
    #         if value == "":
    #             setattr(self, key, None)
    #     # Validating the parsing results of all fields and setting the job vacancy parsing status
    #     # Проверка результатов парсинга всех полей и установка статуса парсинга вакансии
    #     self._set_parsing_status()

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
        source (Mapped[RawMessage]): link to the original message
        vacancies_in_30d (Mapped[int]): number of job vacancies in the last 30 days
        candidates_online (Mapped[int]): number of candidates online
        min_salary (Mapped[int]): minimum salary
        max_salary (Mapped[int]): maximum salary
        responses_to_vacancies (Mapped[int]): number of responses per vacancy
        vacancies_per_week (Mapped[int]): number of job vacancies in the last week
        candidates_per_week (Mapped[int]): number of candidates in the last week
    """
    __tablename__ = TableNames.STATISTIC.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vacancies_in_30d: Mapped[int] = mapped_column(Integer, nullable=True)
    candidates_online: Mapped[int] = mapped_column(Integer, nullable=True)
    min_salary: Mapped[int] = mapped_column(Integer, nullable=True)
    max_salary: Mapped[int] = mapped_column(Integer, nullable=True)
    responses_to_vacancies: Mapped[int] = mapped_column(Integer, nullable=True)
    vacancies_per_week: Mapped[int] = mapped_column(Integer, nullable=True)
    candidates_per_week: Mapped[int] = mapped_column(Integer, nullable=True)
    parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    # Relationships to 'RawMessage' table
    raw_message_id: Mapped[int] = mapped_column(Integer,
                                                ForeignKey(f'{TableNames.RAW_MESSAGES.value}.id', ondelete='CASCADE'),
                                                index=True, unique=True)
    raw_message: Mapped['RawMessage'] = relationship(back_populates='statistic')


class Service(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for service messages
    Класс-модель для служебных сообщений
    Attributes:
        id (Mapped[int]): database record ID
        source (Mapped[RawMessage]): link to the original message
        text (Mapped[Optional[str]]): text of message
    """
    __tablename__ = TableNames.SERVICE.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Relationships to 'RawMessage' table
    raw_message_id: Mapped[int] = mapped_column(Integer,
                                                ForeignKey(f'{TableNames.RAW_MESSAGES.value}.id', ondelete='CASCADE'),
                                                index=True, unique=True)
    raw_message: Mapped['RawMessage'] = relationship(back_populates='service')


class VacancyWeb(Base):
    """
    Class model for job vacancy URLs on the website
    Класс-модель для URL-адресов вакансий на сайте
    """
    __tablename__ = TableNames.VACANCY_WEB.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    redirect_url: Mapped[str] = mapped_column(String, nullable=True)
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_check: Mapped[Optional[datetime]]
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    # Relationships to 'Vacancy' table
    vacancy_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.VACANCIES.value}.id',
                                                                ondelete='CASCADE'), nullable=True, index=True)
    vacancy: Mapped['Vacancy'] = relationship(back_populates='vacancy_web')


class MessageSource(Base):
    """
    A model class for message sources
    Класс-модель (справочник) для источников сообщений
    """
    __tablename__ = TableNames.MESSAGE_SOURCE.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Relationships to 'RawMessage' table
    raw_message: Mapped[List['RawMessage']] = relationship(back_populates='message_source')


class MessageType(Base):
    """
    A model class for message types
    Класс-модель (справочник) для типов сообщений
    """
    __tablename__ = TableNames.MESSAGE_TYPE.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Relationships to 'raw_messages' table
    raw_message: Mapped[List['RawMessage']] = relationship(back_populates='message_type')


class VacancyAttribute(Base):
    """
    A model class for vacancy attributes names
    Класс-модель (справочник) для названий атрибутов вакансий
    """
    __tablename__ = TableNames.VACANCY_ATTRS.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    type: Mapped[str] = mapped_column(String)
    # Relationships to 'VacancyData' table
    vacancy_attr: Mapped[List['VacancyData']] = relationship(back_populates='attr_name')


# TypeVar for model classes, bound to Base
ModelType = TypeVar('ModelType', bound=Base)


# def get_vacancy_attr(attr: str) -> str:
#     """
#     Пользовательская функция для обработки параметра вакансии при получении его из разных источников
#     """
#     return ' '.join([attr, '1'])


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
                if hasattr(existing, key):
                    setattr(existing, key, value)
            added = False
        else:
            # Create a new record / Создаем новую запись
            existing = model_class(**{**filter_fields, **update_fields})
            self.session.add(existing)
            self.session.flush()  # Flush to get the ID if it's an autoincrement field
            added = True
        return existing, added

    @staticmethod
    def setup_database_connection():
        """
        Настройка параметров подключения к базе данных SQLite
        """

        # SQLite database setting
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _):  # _ используется вместо необязательного параметра connection_record
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")  # Enabling foreign key constraints
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            cursor.execute("PRAGMA synchronous=NORMAL")  # Быстрее запись
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB кеша
            cursor.execute("PRAGMA temp_store=MEMORY")  # Временные данные в RAM
            cursor.close()
            # # Регистрируем пользовательские функции в SQLite
            # dbapi_conn.create_function("vac_attr", 1, get_vacancy_attr)

    def __init__(self):
        """
        Initializes the database handler by creating an engine, a session, and the necessary tables.
        Инициализирует обработчик базы данных, создавая движок, сессию и необходимые таблицы.
        """

        # Connecting to the database. Creating and setup a database connection
        # Подключение к базе данных. Создаем соединение с базой данных и настраиваем его
        self.engine = create_engine(f'sqlite:///{GlobalConst.database_file}')
        self.setup_database_connection()
        # # Пересоздаем представление CreateVacancyFinal
        # sql_text = f'DROP VIEW IF EXISTS {TableNames.create_vacancy_final.value}'
        # self.engine.connect().execute(text(sql_text))
        # # Формируем SQL инструкцию для создания View после создания всех таблиц
        # vac_t = TableNames.vacancy_base.value
        # vac_sour_t = TableNames.vacancy_sources.value
        # select_str = f'vac_attr({vac_t}.domain) as domain, {vac_sour_t}.location, {vac_sour_t}.id'
        # create_view = DDL("""
        #     CREATE VIEW IF NOT EXISTS """ + TableNames.create_vacancy_final.value + """ AS
        #     SELECT """ + select_str + """
        #     FROM """ + vac_t + """
        #     INNER JOIN """ + vac_sour_t + """
        #     ON """ + vac_t + """.id = """ + vac_sour_t + """.vacancy_id
        # """)
        # # Привязываем создание VIEW к событию после создания таблиц
        # event.listen(Base.metadata, 'after_create', create_view)
        # Creating tables in the database if they do not exist. Crating session
        # Создаем таблицы в базе данных, если они отсутствуют. Создаем сессию
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        # Обновляем или создаем статические таблицы-справочники.
        # Источники сообщений
        for message_source in MessageSources:
            self.upsert_record(MessageSource, {'id': message_source.value},
                               {'name': message_source.name})
        # Типы сообщений
        for message_type in MessageTypes:
            self.upsert_record(MessageType, {'id': message_type.type_id},
                               {'name': message_type.name})
        self.session.commit()
        # Атрибуты вакансий
        for parameter in VacancyAttrs:
            self.upsert_record(VacancyAttribute, {'id': parameter.attr_id},
                               {'name': parameter.name, 'type': parameter.attr_type})
        self.session.commit()

        # result = self.engine.connect().execute(text("SELECT vac_attr('test')")).scalar()
        # print(result)
        # self.vacancy_final_create()

    # def vacancy_final_create(self):
    #     # Удаляем таблицу со списком вакансий
    #     sql_text = f'DROP TABLE IF EXISTS {TableNames.vacancy_final.value}'
    #     self.engine.connect().execute(text(sql_text))
    #     # Пересоздаем таблицу со списком вакансий с учетом вычисляемых полей
    #     sql_text = f'CREATE TABLE {TableNames.vacancy_final.value} AS SELECT * FROM {TableNames.create_vacancy_final.value}'
    #     self.engine.connect().execute(text(sql_text))
    #     self.session.commit()


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

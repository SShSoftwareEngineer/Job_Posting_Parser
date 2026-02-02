"""
The module contains model classes, functions, and constants for working with an SQLite database using SQLAlchemy.
Модуль содержит классы моделей, функции и константы для работы с базой данных SQLite с использованием SQLAlchemy.

Classes:
    Base(DeclarativeBase): a declarative class for creating tables in the database
    RawMessage: A model class for original Telegram messages
    VacancyData: A model class for vacancies data
    Vacancy: A model class for vacancy messages
    Statistic: A model class for statistics messages
    Service: A model class for service messages
    VacancyWeb: A model class for job vacancy URLs on the website
    MessageSource: A model class for message sources
    MessageType: A model class for message types
    VacancyAttribute: A model class for vacancy attributes names
    DatabaseHandler: A class to represent handle database operations
Constants:
    ModelType: TypeVar for model classes, bound to Base
vacancy_vacancy_data_links: Table implementing a many-to-many relationship between the Vacancy and VacancyData tables
db_handler: An instance of DatabaseHandler for database operations
"""

from datetime import datetime
from typing import Any, Optional, Type, TypeVar, List
from sqlalchemy import create_engine, Integer, ForeignKey, Text, String, event, Engine, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from configs.config import GlobalConst, TableNames, MessageSources, MessageTypes, VacancyAttrs


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """
    A declarative class for creating tables in the database
    Декларативный класс для создания таблиц в базе данных
    """


# TypeVar for model classes, bound to Base / TypeVar для классов моделей, связанных с Base
ModelType = TypeVar('ModelType', bound=Base)

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
        date (Mapped[datetime]): message date
        message_id (Mapped[int]): Telegram message ID
        email_uid (Mapped[int]): Email message UID
        text (Mapped[str]): message text
        html (Mapped[str]): message HTML
        raw_parsing_error (Mapped[str]): error during raw message parsing
        message_source_id (Mapped[int]): link to the message source
        message_type_id (Mapped[int]): link to the message type
    """

    __tablename__ = TableNames.RAW_MESSAGES.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[datetime]
    message_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    email_uid: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=True)
    html: Mapped[str] = mapped_column(Text, nullable=True)
    raw_parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    # Relationships to 'Vacancy' table / Связи с таблицей 'Vacancy'
    vacancy: Mapped[List['Vacancy']] = relationship(back_populates='raw_message', cascade='all, delete-orphan')
    # Relationships to 'Statistic' table / Связи с таблицей 'Statistic'
    statistic: Mapped['Statistic'] = relationship(back_populates='raw_message', uselist=False,
                                                  cascade='all, delete-orphan')
    # Relationships to 'Service' table / Связи с таблицей 'Service'
    service: Mapped['Service'] = relationship(back_populates='raw_message', uselist=False, cascade='all, delete-orphan')
    # Relationships to 'MessageSource' table / Связи с таблицей 'MessageSource'
    message_source_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.MESSAGE_SOURCE.value}.id'),
                                                   index=True)
    message_source: Mapped['MessageSource'] = relationship(back_populates='raw_message')
    # Relationships to 'MessageType' table / Связи с таблицей 'MessageType'
    message_type_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.MESSAGE_TYPE.value}.id'),
                                                 index=True)
    message_type: Mapped['MessageType'] = relationship(back_populates='raw_message')


class VacancyData(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for vacancies data
    Класс-модель для параметров вакансий

    Attributes:
        id (Mapped[int]): database record ID
        attr_value (Mapped[str]): attribute value
        attr_source_id (Mapped[int]): source ID of the attribute
        attr_name_id (Mapped[int]): link to the attribute name
    """

    __tablename__ = TableNames.VACANCY_DATA.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    attr_value: Mapped[str] = mapped_column(String, nullable=False)
    # Relationships to 'MessageSource' table / Связи с таблицей 'MessageSource'
    attr_source_id: Mapped[int] = mapped_column(Integer)
    # Relationships to 'VacancyAttribute' table / Связи с таблицей 'VacancyAttribute'
    attr_name_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.VACANCY_ATTRS.value}.id'), index=True)
    attr_name: Mapped['VacancyAttribute'] = relationship(back_populates='vacancy_attr')
    # Relationships to 'Vacancy' table, many-to-many / Связи с таблицей 'Vacancy', многие-ко-многим
    vacancy: Mapped[List['Vacancy']] = relationship(secondary=vacancy_vacancy_data_links, back_populates='vacancy_data')


class Vacancy(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for vacancy messages
    Класс-модель для сообщений о вакансиях

    Attributes:
        id (Mapped[int]): database record ID
        data_hash (Mapped[str]): hash of parameters as vacancy identifier
        message_parsing_error (Mapped[str]): service parameters used for parsing debugging
        web_parsing_error (Mapped[str]): service parameters used for parsing debugging
        raw_message_id (Mapped[int]): link to the original message
    """

    __tablename__ = TableNames.VACANCIES.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Hash parameters as a vacancy identifier / Hash параметров как идентификатор вакансии
    data_hash: Mapped[str] = mapped_column(String, nullable=True)
    # Service parameters used for parsing debugging / Служебные параметры, используемые при отладке парсинга
    message_parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    web_parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    # Relationships to 'RawMessage' table / Связи с таблицей 'RawMessage'
    raw_message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.RAW_MESSAGES.value}.id'), index=True,
                                                nullable=True)
    raw_message: Mapped['RawMessage'] = relationship(back_populates='vacancy')
    # Relationships to 'VacancyWeb' table / Связи с таблицей 'VacancyWeb'
    vacancy_web: Mapped[List['VacancyWeb']] = relationship(back_populates='vacancy', cascade='all, delete-orphan')
    # Relationships to 'VacancyData' table, many-to-many / Связи с таблицей 'VacancyData', многие-ко-многим
    vacancy_data: Mapped[List['VacancyData']] = relationship(secondary=vacancy_vacancy_data_links,
                                                             back_populates='vacancy')


class Statistic(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for statistics messages
    Класс-модель для сообщений со статистикой

    Attributes:
        id (Mapped[int]): database record ID
        vacancies_in_30d (Mapped[int]): number of vacancies in the last 30 days
        candidates_online (Mapped[int]): number of candidates online
        min_salary (Mapped[int]): minimum salary
        max_salary (Mapped[int]): maximum salary
        responses_to_vacancies (Mapped[int]): number of responses to vacancies
        vacancies_per_week (Mapped[int]): number of vacancies per week
        candidates_per_week (Mapped[int]): number of candidates per week
        stat_parsing_error (Mapped[str]): error during statistics parsing
        raw_message_id (Mapped[int]): link to the original message
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
    stat_parsing_error: Mapped[str] = mapped_column(String, nullable=True)
    # Relationships to 'RawMessage' table / Связи с таблицей 'RawMessage'
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
        text (Mapped[str]): service message text
        raw_message_id (Mapped[int]): link to the original message
    """

    __tablename__ = TableNames.SERVICE.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Relationships to 'RawMessage' table / Связи с таблицей 'RawMessage'
    raw_message_id: Mapped[int] = mapped_column(Integer,
                                                ForeignKey(f'{TableNames.RAW_MESSAGES.value}.id', ondelete='CASCADE'),
                                                index=True, unique=True)
    raw_message: Mapped['RawMessage'] = relationship(back_populates='service')


class VacancyWeb(Base):  # pylint: disable=too-few-public-methods
    """
    Class model for job vacancy URLs on the website
    Класс-модель для URL-адресов вакансий на сайте

    Attributes:
        id (Mapped[int]): database record ID
        url (Mapped[str]): vacancy URL
        raw_html (Mapped[Optional[str]]): raw HTML content of the vacancy page
        last_check (Mapped[Optional[datetime]]): datetime of the last URL check
        status_code (Mapped[Optional[int]]): HTTP status code of the last request
        parsing_date (Mapped[Optional[datetime]]): datetime of parsing
        vacancy_id (Mapped[int]): link to the vacancy
    """

    __tablename__ = TableNames.VACANCY_WEB.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_check: Mapped[Optional[datetime]]
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parsing_date: Mapped[Optional[datetime]]
    # Relationships to 'Vacancy' table / Связи с таблицей 'Vacancy'
    vacancy_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TableNames.VACANCIES.value}.id',
                                                                ondelete='CASCADE'), nullable=True, index=True)
    vacancy: Mapped['Vacancy'] = relationship(back_populates='vacancy_web')


class MessageSource(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for message sources
    Класс-модель (справочник) для источников сообщений

    Attributes:
        id (Mapped[int]): database record ID
        name (Mapped[str]): source name
    """

    __tablename__ = TableNames.MESSAGE_SOURCE.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Relationships to 'RawMessage' table / Связи с таблицей 'RawMessage'
    raw_message: Mapped[List['RawMessage']] = relationship(back_populates='message_source')


class MessageType(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for message types
    Класс-модель (справочник) для типов сообщений

    Attributes:
        id (Mapped[int]): database record ID
        name (Mapped[str]): type name
    """

    __tablename__ = TableNames.MESSAGE_TYPE.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Relationships to 'raw_messages' table / Связи с таблицей 'raw_messages'
    raw_message: Mapped[List['RawMessage']] = relationship(back_populates='message_type')


class VacancyAttribute(Base):  # pylint: disable=too-few-public-methods
    """
    A model class for vacancy attributes names
    Класс-модель (справочник) для названий атрибутов вакансий

    Attributes:
        id (Mapped[int]): database record ID
        name (Mapped[str]): vacancy attribute name
        type (Mapped[str]): vacancy attribute type
    """

    __tablename__ = TableNames.VACANCY_ATTRS.value  # Table name in the database / Имя таблицы в базе данных
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    type: Mapped[str] = mapped_column(String)
    # Relationships to 'VacancyData' table / Связи с таблицей 'VacancyData'
    vacancy_attr: Mapped[List['VacancyData']] = relationship(back_populates='attr_name')


class DatabaseHandler:
    """
    A class to represent handle database operations.
    Класс для представления операций с базой данных.

    Attributes:
        engine: SQLAlchemy engine for database connection
        session: SQLAlchemy session for database operations
        upsert_record: method for searching and updating/creating records in any database model
    """

    engine: Engine
    session: Session

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
            bool: True if a new record was created, False if an existing record was updated
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
        Configuring SQLite database connection settings
        Настройка параметров подключения к базе данных SQLite
        """

        # SQLite database setting / Параметры базы данных SQLite
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _):
            # "_" used instead of the optional connection_record parameter
            # "_" используется вместо необязательного параметра connection_record
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")  # Enabling foreign key constraints
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            cursor.execute("PRAGMA synchronous=NORMAL")  # Faster recording
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
            cursor.execute("PRAGMA temp_store=MEMORY")  # Temporary data in RAM
            cursor.close()
            # # Registering user functions in SQLite / Регистрируем пользовательские функции в SQLite
            # dbapi_conn.create_function("vac_attr", 1, get_vacancy_attr)

    def __init__(self):
        """
        Initializes the database handler by creating an engine, a session, and the necessary tables.
        Инициализирует обработчик базы данных, создавая движок, сессию и необходимые таблицы.
        """

        # Connecting to the database. Creating and setup a database connection and constants tables
        # Создаем соединение с базой данных и настраиваем его, а также таблицы-справочники констант
        self.engine = create_engine(f'sqlite:///{GlobalConst.database_file}')
        self.setup_database_connection()

        # Creating tables in the database if they do not exist. Crating session
        # Создаем таблицы в базе данных, если они отсутствуют. Создаем сессию
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        # We update or create static reference tables / Обновляем или создаем статические таблицы-справочники

        # Sources of messages table / Таблица-справочник "Источники сообщений"
        for message_source in MessageSources:
            self.upsert_record(MessageSource, {'id': message_source.value},
                               {'name': message_source.name})
        # Types of messages table / Таблица-справочник "Типы сообщений"
        for message_type in MessageTypes:
            self.upsert_record(MessageType, {'id': message_type.type_id},
                               {'name': message_type.name})
        self.session.commit()
        # Job attributes table / Таблица-справочник "Атрибуты вакансий"
        for parameter in VacancyAttrs:
            self.upsert_record(VacancyAttribute, {'id': parameter.attr_id},
                               {'name': parameter.name, 'type': parameter.attr_type})
        self.session.commit()


# Create an instance of DatabaseHandler() / Создаем экземпляр DatabaseHandler()
db_handler = DatabaseHandler()

if __name__ == '__main__':
    pass

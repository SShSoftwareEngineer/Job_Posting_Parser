from dataclasses import dataclass
from datetime import datetime
from enum import Enum, StrEnum
from pathlib import Path


@dataclass
class GlobalConst:
    private_settings_file = Path(
        'configs') / '.env'  # Confidential data file name / Имя файла с конфиденциальными данными
    database_file = 'full_vacancies.db'  # SQLite file name / Имя файла SQLite базы данных
    excel_file = 'exported_data.xlsx'  # Exported MS Excel file name / Имя экспортируемого файла MS Excel
    parse_config_file = Path('config.toml')  # Configuration data file / Имя файла конфигурации
    timeout_seconds = 10  # Timeout for HTTP requests in seconds / Таймаут для HTTP запросов в секундах
    # Maximum number of concurrent HTTP requests
    # Максимальное количество одновременных HTTP запросов
    max_concurrent_requests = 10
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'  # User-Agent for HTTP requests / User-Agent для HTTP запросов
    start_date = datetime(2020, 1, 1)


class MessageSources(Enum):
    """
    Constants for different sources of messages.
    """
    WEB = 1
    EMAIL = 2
    TELEGRAM = 3


class MessageTypes(Enum):
    """
    Constants for different types of messages.
    """
    TG_VACANCY = 1, 'tg_vacancy'
    TG_STATISTIC = 2, 'tg_statistic'
    TG_SERVICE = 3, 'tg_service'
    TG_UNKNOWN = 4, 'tg_unknown'
    EMAIL_VACANCY = 5, 'email_vacancy'
    EMAIL_UNKNOWN = 6, 'email_unknown'

    def __init__(self, type_id: int, config_name: str):
        """
        Initializes the MessageTypes enum.
        Инициализация MessageTypes enum.
        Attributes:
            type_id (int): The ID of the file type.
            config_name (str): Type name in config.toml file.
        """
        self.type_id = type_id
        self.config_name = config_name

    @classmethod
    def get_message_type_by_config_name(cls, config_name: str) -> 'MessageTypes':
        """
        Returns the MessageTypes for a given type message.
        Возвращает MessageTypes для заданного сообщения.
        Attributes:
            config_name (str): The type name in config file.
        Returns:
            MessageTypes: The corresponding MessageTypes enum member.
        """

        result = MessageTypes.TG_UNKNOWN
        for item in cls:
            if item.config_name == config_name:
                result = item
        return result

    @classmethod
    def get_message_type_id(cls, message_type: 'MessageTypes') -> int:
        """
        Returns the MessageTypes ID for a given message type.
        Возвращает MessageTypes ID для заданного типа сообщения.
        Attributes:
            message_type (MessageTypes): The message type.
        Returns:
            ID: The corresponding ID.
        """

        result = MessageTypes.TG_UNKNOWN.value[0]
        for item in cls:
            if item.name == message_type.name:
                result = item.value[0]
        return result


class HttpStatusCodes(Enum):
    """
    Constants for HTTP status codes.
    """
    OK = 200
    NOCONTENT = 204
    BADREQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOTFOUND = 404
    TOOMANYREQUESTS = 429
    INTERNALSERVERERROR = 500
    BADGATEWAY = 502
    SERVICEUNAVAILABLE = 503


class TableNames(Enum):
    """
    Table names in the database for different types of messages.
    Имена таблиц в базе данных для разных типов сообщений.
    """
    RAW_MESSAGES = 'raw_messages'
    VACANCIES = 'vacancies'
    VACANCY_DATA = 'vacancy_data'
    VACANCY_DATA_VACANCIES_LINKS = 'vacancy_data_vacancies_links'
    VACANCY_ATTRS = 'vacancy_attrs'
    VACANCY_WEB = 'vacancy_web'
    STATISTIC = 'statistic'
    SERVICE = 'service'
    MESSAGE_SOURCE = 'message_sources'
    MESSAGE_TYPE = 'message_types'

    # # View for create vacancies list
    # create_vacancy_final = 'create_vacancy_final'

    @staticmethod
    def get_table_names() -> list[str]:
        """
        Returns a list of model names and their corresponding table names.
        """
        return [item.value for item in TableNames]


class VacancyAttrs(Enum):
    """
    Job parameter names.
    Наименование параметров вакансий.
    """

    POSITION = 1, 'string'
    LOCATION = 2, 'string'
    EXPERIENCE = 3, 'float'
    MAIN_TECH = 4, 'string'
    TECH_STACK = 5, 'string'
    LINGVO = 6, 'string'
    SALARY_FROM = 7, 'integer'
    SALARY_TO = 8, 'integer'
    JOB_DESC_PREV = 9, 'string'
    COMPANY = 10, 'string'
    COMPANY_TYPE = 11, 'string'
    DOMAIN = 12, 'string'
    OFFICES = 13, 'string'
    EMPLOYMENT = 14, 'string'
    CANDIDATE_LOCATIONS = 15, 'string'
    SUBSCRIPTION = 16, 'string'
    URL = 17, 'string'
    JOB_DESC = 18, 'string'
    NOTES = 19, 'string'

    def __init__(self, attr_id: int, attr_type: str):
        """
        Initializes the VacancyAttrs enum.
        Инициализация VacancyAttrs enum.
        Attributes:

        """
        self.attr_id = attr_id
        self.attr_type = attr_type

    @classmethod
    def get_name_by_id(cls, attr_id: int) -> str:
        """
        Returns the VacancyAttrs.name in lower case for a given attr_id.
        Возвращает VacancyAttrs.name для заданного attr_id.
        Attributes:
            attr_id (int): The ID of attribute.
        Returns:
            str: The corresponding name of VacancyAttrs enum member.
        """

        result = 0
        for item in cls:
            if item.attr_id == attr_id:
                result = item.name.lower()
        return result


class ReportLabel(StrEnum):
    EMAIL_MESS = "Email messages received"
    EMAIL_RAW = "Email RAW messages processed"
    EMAIL_RAW_ADD = "Email RAW messages added"
    EMAIL_RAW_UPD = "Email RAW messages updated"
    EMAIL_VAC = "Email vacancy messages processed"
    EMAIL_VAC_ADD = "Email vacancy messages added"
    EMAIL_VAC_UPD = "Email vacancy messages updated"
    EMAIL_VAC_ERR = "Email vacancy parsing errors"
    EMAIL_URL_ADD = "Email vacancy URL added"
    EMAIL_URL_UPD = "Email vacancy URL updated"
    TG_MESS = "Telegram messages received"
    TG_RAW = "Telegram RAW vacancy messages processed"
    TG_VAC = "Telegram Vacancy messages processed"
    TG_STAT = "Telegram Statistic messages processed"
    TG_SERV = "Telegram Service messages processed"
    TG_ERR = "Telegram message parsing errors"
    TG_URL_ADD = "Telegram vacancy URL added"
    TG_URL_UPD = "Telegram vacancy URL updated"
    WEB_VAC = "Web vacancy processed"
    WEB_ERR = "Web vacancy parsing errors"


# WEB_URL updated       30
# WEB_VACANCY_PARSED    30

if __name__ == '__main__':
    pass

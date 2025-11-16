from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass
class GlobalConst:
    private_settings_file = Path(
        'configs') / '.env'  # Confidential data file name / Имя файла с конфиденциальными данными
    database_file = 'full_vacancies.db'  # SQLite file name / Имя файла SQLite базы данных
    excel_file = 'exported_data.xlsx'  # Exported MS Excel file name / Имя экспортируемого файла MS Excel
    parse_config_file = 'configs/config.json'  # Configuration data file in JSON format / Имя файла конфигурации в формате JSON


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
    TG_VACANCY = (1, 'tg_vacancy')
    TG_STATISTIC = (2, 'tg_statistic')
    TG_SERVICE = (3, 'tg_service')
    TG_UNKNOWN = (4, 'tg_unknown')
    EMAIL_VACANCY = (5, 'email_vacancy')
    EMAIL_UNKNOWN = (6, 'email_unknown')

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


@dataclass
class TableNames(Enum):
    """
    Table names in the database for different types of messages.
    Имена таблиц в базе данных для разных типов сообщений.
    """
    raw_message = 'raw_messages'
    vacancy = 'vacancy'
    vacancy_sources = 'vacancy_sources'
    statistic = 'statistic'
    service = 'service'
    message_source = 'message_sources'
    message_type = 'message_types'
    vacancy_web = 'vacancy_web'
    # View for vacancies
    vacancies = 'vacancies'

    @staticmethod
    def get_table_names() -> list[str]:
        """
        Returns a list of model names and their corresponding table names.
        """
        return [item.value for item in TableNames]


if __name__ == '__main__':
    pass

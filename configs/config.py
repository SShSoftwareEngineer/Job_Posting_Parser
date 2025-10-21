from enum import Enum
from pathlib import Path


class GlobalConst:
    private_settings_file = Path(
        'configs') / f'.env'  # Confidential data file name / Имя файла с конфиденциальными данными
    database_file = f'full_vacancies.db'  # SQLite and MS Excel file name / Имя файла SQLite и MS Excel для экспорта базы данных
    parse_config_file = 'configs/config.json'  # Configuration file name in JSON format / Имя файла конфигурации в формате JSON


class MessageSources(Enum):
    """
    Constants for different sources of messages.
    """
    Email = 1
    Telegram = 2


class MessageTypes(Enum):
    """
    Constants for different types of messages.
    """
    Source = 1
    Vacancy = 2
    Statistic = 3
    Service = 4
    Unknown = 5


class HttpStatusCodes(Enum):
    """
    Constants for HTTP status codes.
    """
    Ok = 200
    NoContent = 204
    BadRequest = 400
    Unauthorized = 401
    Forbidden = 403
    Not_Found = 404
    TooManyRequests = 429
    InternalServerError = 500
    BadGateway = 502
    ServiceUnavailable = 503

# Table names in the database for different types of messages / Имена таблиц в базе данных для разных типов сообщений
class TableNames(Enum):
    """
    Constants for database table names.
    """
    raw_message = 'raw_messages'
    vacancy = 'vacancies'
    statistic = 'statistics'
    service = 'service'
    message_source = 'message_sources'
    message_type = 'message_types'
    vacancy_web = 'vacancies_web'

    @staticmethod
    def get_table_names() -> list[str]:
        """
        Returns a list of model names and their corresponding table names.
        """
        return [item.value for item in TableNames]


if __name__ == '__main__':
    pass

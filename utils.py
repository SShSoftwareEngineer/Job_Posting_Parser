import re

from dateutil.parser import parse


def load_env(file_path: str) -> dict:
    """
    Loading confidential data for working with the Telegram API from the `.env` file.
    Загрузка конфиденциальных данных для работы с Telegram API из файла .env

    Arguments:
    file_path (str): a confidential data file name
    Returns:
    dict: a confidential data dictionary
    """
    env_vars = {}
    with open(file_path, 'r', encoding='utf-8') as file_env:
        for line in file_env:
            if not line.strip().startswith('#') and '=' in line:
                key, value = line.strip().split('=')
                if value.startswith("'") and value.endswith("'") or value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                env_vars[key] = value
    return env_vars


def parse_date_string(date_str: str):
    """
    Parses a date string and returns a datetime object.
    """
    if not date_str:
        return None
    try:
        return parse(date_str, dayfirst=True)
    except (ValueError, OverflowError):
        return None


def str_to_numeric(value: str | None) -> int | float | None:
    """
    Safe conversion of a string to a numeric value (int or float)
    Безопасное преобразование строки в числовое значение (int или float)
    """
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
    """
    Convert HTML text to plain text
    Преобразование HTML-текста в обычный текст
    """
    # Replacing '\n' sequences with spaces.
    # Заменяем последовательности '\n' на пробелы
    text = re.sub(r'\n+', ' ', html)
    # Replacing tags <p>, <div> with '\n'
    # Заменяем теги <p>, <div> на '\n'
    text = re.sub(r'</?(p|div)[^>]*>', '\n', text)
    # Replacing tag <br> with '\n'
    # Заменяем тег <br> на '\n'
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Remove all remaining HTML tags
    # Удаляем все оставшиеся HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    # Removing extra spaces and empty lines
    # Убираем лишние пробелы и пустые строки
    text = re.sub(r'\n+', '\n', text).strip()
    # Removing extra spaces at the beginning and end of each line
    # Убираем лишние пробелы в начале и конце каждой строки
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
    # Removing extra spaces in lines
    # Удаляем лишние пробелы в строках
    text = re.sub(r' +', ' ', text)
    return text


if __name__ == '__main__':
    pass

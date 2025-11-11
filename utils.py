import re
from datetime import datetime

from dateutil.parser import parse


def parse_date_string(date_str: str) -> datetime | None:
    """
    Parses a date string and returns a datetime object.
    Парсит строку даты и возвращает объект datetime.
    Attributes:
        date_str (str): Date string to parse
    Returns:
        datetime | None: Parsed datetime object or None if parsing fails
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

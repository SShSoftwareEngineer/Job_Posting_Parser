""" Модуль содержит классы-модели, функции и константы для работы с базой данных SQLite с использованием SQLAlchemy

HTTP_ERRORS - словарь с описанием ошибок HTTP-запросов
class Base(DeclarativeBase) - декларативный класс для создания таблиц в базе данных
class SourceMessage(Base) - класс-модель для исходных сообщений Telegram
class VacancyMessage(Base) - класс-модель для сообщений с вакансиями
class StatisticMessage(Base) - класс-модель для сообщений со статистикой
class ServiceMessage(Base) - класс-модель для служебных сообщений
def export_data_to_excel() - функция для экспорта данных из базы данных в файл MS Excel
session - объект сессии для работы с базой данных
"""

import os
import re
from datetime import datetime
from typing import Any, Optional, cast
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Integer, ForeignKey, Text, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

from config_handler import TABLE_NAMES, config

# Имя файла MS Excel для экспорта базы данных
_OUTPUT_EXCEL_FILE = 'result.xlsx'

HTTP_ERRORS = {
    403: 'Error 403 Forbidden',
    404: 'Error 404 Not Found',
    429: 'Error 429 Too Many Requests',
    "IP blocked": "Error 403 Forbidden or 429 Too Many Requests"
}


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """ Декларативный класс """


class SourceMessage(Base):  # pylint: disable=too-few-public-methods
    """ Класс-модель для исходных сообщений Telegram

    Attributes:
    id (Mapped[int]): идентификатор записи в БД
    message_id (Mapped[int]): идентификатор сообщения Telegram
    date (Mapped[datetime]): дата сообщения
    message_type (Mapped[str]): тип сообщения
    text (Mapped[str]): текст сообщения
    """
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
        """ Инициализация объекта SourceMessage. Определение типа сообщения по содержимому """
        super().__init__(**kw)
        self._set_message_type(config.message_signs)

    def _set_message_type(self, message_signs: dict):
        """ Определяет тип сообщения по содержимому """
        for message_type, patterns in message_signs.items():
            matching = re.search(f"{'|'.join(patterns)}", self.text)
            if matching:
                self.message_type = message_type
                return


class VacancyMessage(Base):  # pylint: disable=too-few-public-methods, disable=too-many-instance-attributes
    """ Класс-модель для сообщений о вакансиях

    Attributes:
    id (Mapped[int]): идентификатор записи в БД
    message_id (Mapped[int]): идентификатор сообщения Telegram
    source (Mapped[SourceMessage]): ссылка на исходное сообщение
    text (Mapped[str]): текст сообщения
    t_position (Mapped[str]): должность, позиция
    company (Mapped[str]): компания
    location (Mapped[str]): локация компании
    t_experience (Mapped[int]): опыт работы
    min_salary (Mapped[int]): минимальная заработная плата
    max_salary (Mapped[int]): максимальная заработная плата
    url (Mapped[str]): URL вакансии на сайте
    subscription (Mapped[str]): подписка на сообщения о вакансии
    raw_html (Mapped[str]): HTML-код страницы вакансии на сайте
    h_position (Mapped[str]): должность, позиция на сайте
    description (Mapped[str]): описание вакансии на сайте
    lingvo (Mapped[str]): требования к английскому
    h_experience (Mapped[str]): опыт работы на сайте
    work_type (Mapped[str]): тип работы
    candidate_locations (Mapped[str]): рассматриваемые локации кандидатов
    main_tech (Mapped[str]): основная технология кандидатов
    tech_stack (Mapped[str]): технический стек
    domain (Mapped[str]): домен компании
    company_type (Mapped[str]): тип компании
    offices (Mapped[str]): локация офисов компании
    notes (Mapped[str]): заметки
    """

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
    # Служебные параметры, используемые для отладки парсинга
    parsing_status: Mapped[str] = mapped_column(String, nullable=True)
    temp_card: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __init__(self, **kw: Any):
        """ Инициализация объекта VacancyMessage. Парсинг текста сообщения и HTML-кода страницы вакансии """
        super().__init__(**kw)
        vacancy_text_signs = config.message_configs.vacancy.text_parsing_signs
        vacancy_html_signs = config.message_configs.vacancy.html_parsing_signs
        # Извлечение позиции, названия компании из текста сообщения Telegram
        self._set_position_company(vacancy_text_signs["position_company"])
        # Извлечение локации компании, опыта из текста сообщения Telegram
        self._set_location_experience(vacancy_text_signs["location_experience"])
        # Извлечение информации о зарплате из текста сообщения Telegram
        self._set_salary(config.re_patterns.salary_range, config.re_patterns.salary)
        # Извлечение URL вакансии на сайте из текста сообщения Telegram
        self._set_url(config.get_url_pattern())
        # Извлечение информации о подписке рассылки из текста сообщения Telegram
        self._set_subscription(vacancy_text_signs["subscription"])
        # Парсинг информации о вакансии из HTML-кода страницы вакансии на сайте
        self._vacancy_html_parsing(vacancy_html_signs)
        for key, value in vars(self).items():
            if value == "":
                setattr(self, key, None)
        # Проверка результатов парсинга всех полей и установка статуса парсинга вакансии
        self._set_parsing_status()

    def _set_position_company(self, splitter: list[str]):
        """ Извлечение позиции, названия компании из текста сообщения Telegram """
        parsing_str = re.sub(r'[*_`]+', '', str(self.text).split('\n', maxsplit=1)[0]).replace('  ', ' ')
        matching = re.split(f"{'|'.join(splitter)}", parsing_str)
        if matching:
            self.t_position = matching[0]
            if len(matching) > 1:
                self.company = matching[1]
        else:
            self.t_position = parsing_str

    def _set_location_experience(self, pattern: list[str]):
        """ Извлечение локации компании, опыта из текста сообщения Telegram """
        parsing_str = re.sub(r'[*_`]+', '', str(self.text).split('\n')[1]).replace('  ', ' ')
        matching = re.search(f'(.+), {config.re_patterns.numeric}? ?({"|".join(pattern)})', parsing_str)
        if matching:
            self.location = matching.group(1)
            self.t_experience = cast(int | None, str_to_numeric(matching.group(2)))
            if matching.group(2) is None and matching.group(3) is not None:
                self.t_experience = 0

    def _set_salary(self, range_pattern: str, salary_pattern: str):
        """ Извлечение информации о зарплате из текста сообщения Telegram """
        parsing_str = re.sub(r'[*_`]+', '', str(self.text).split('\n')[1]).replace('  ', ' ')
        matching = re.search(fr'{range_pattern}\Z', parsing_str)
        if matching:
            if len(matching.groups()) == 2:
                self.min_salary = cast(int | None, str_to_numeric(matching.group(1)))
                self.max_salary = cast(int | None, str_to_numeric(matching.group(2)))
        else:
            matching = re.search(fr'{salary_pattern}\Z', parsing_str)
            if matching:
                self.min_salary = cast(int | None, str_to_numeric(matching.group(1)))
                self.max_salary = self.min_salary

    def _set_url(self, pattern: str):
        """ Извлечение URL вакансии на сайте из текста сообщения Telegram """
        matching = re.search(pattern, str(self.text))
        if matching:
            self.url = matching.group(0)

    def _set_subscription(self, pattern: list[str]):
        """ Извлечение информации о подписке рассылки из текста сообщения Telegram """
        parsing_str = re.sub(r'[*_`]+', '', str(self.text).rsplit('\n', maxsplit=1)[-1]).replace('  ', ' ')
        matching = re.sub(f'{"|".join(pattern)}', '', parsing_str)
        if matching:
            self.subscription = matching.strip('\"\' *_`')

    def _is_vacancy_html_error(self) -> bool:
        """ Проверка, не вернул ли сервер HTML-страницу с ошибкой """
        if self.raw_html is None:
            return False
        matching = re.search(r'Error \d{3}', self.raw_html)
        if matching and matching.start(0) < 500:
            return True
        return False

    def _safety_add_string(self, field: str, adding_string: str):
        """ Добавление строки в поле, если оно не пустое. Иначе присваивает значение полю """
        if not adding_string:
            return
        if getattr(self, field) is None:
            setattr(self, field, adding_string.strip())
        else:
            if adding_string not in getattr(self, field):
                setattr(self, field, f'{getattr(self, field)}\n{adding_string.strip()}')

    def _vacancy_html_parsing(self, patterns):  # pylint: disable=too-many-branches, disable=too-many-statements
        """ Парсинг информации о вакансии из HTML-кода страницы вакансии на сайте """
        # Проверяем, что сервер вернул HTML-страницу с текстом вакансии
        if self._is_vacancy_html_error():
            return
        # Создаем объект BeautifulSoup для парсинга HTML-страницы с текстом вакансии
        soup = BeautifulSoup(self.raw_html, 'lxml')
        # Получаем заголовок вакансии
        if soup.find('h1').find('span'):
            self.h_position = html_to_text(str(soup.find('h1').find('span')))
        # Получаем описание вакансии
        if soup.find('div', class_=patterns.html_classes.description):
            self.description = html_to_text(str(soup.find('div', class_=patterns.html_classes.description)))
        # Получаем дополнительную информацию о вакансии из "карточки вакансии"
        if soup.find('div', class_=patterns.html_classes.job_card):
            job_card = soup.find('div', class_=patterns.html_classes.job_card)
            ul_tags = job_card.find_all('ul', class_=patterns.html_classes.ul_tags)

            self.temp_card = None

            self.notes = None
            if ul_tags and len(ul_tags) == 3:
                additional_info = []

                # Парсим первый блок: требования к английскому, опыт, тип работы, локации кандидатов
                li_tags = ul_tags[0].find_all('li')
                for li_tag in li_tags:
                    additional_info.append(html_to_text(str(li_tag)))

                self._safety_add_string('temp_card', '\n'.join([x for x in additional_info if x]))

                for i, add_info in enumerate(additional_info):
                    if re.search(f"{'|'.join(patterns.lingvo)}", add_info):
                        self._safety_add_string('lingvo', add_info)
                        additional_info[i] = ''
                    if re.search(f"{'|'.join(patterns.experience)}", add_info):
                        self.h_experience = add_info
                        additional_info[i] = ''
                    if re.search(f"{'|'.join(patterns.work_type)}", add_info):
                        self.work_type = add_info
                        additional_info[i] = ''
                    if re.search(f"{'|'.join(patterns.candidate_locations)}", add_info):
                        self.candidate_locations = add_info.split('\n')[0]
                        additional_info[i] = ''
                self._safety_add_string('notes', '\n'.join([x for x in additional_info if x]))

                # Парсим второй блок: основная технология, технический стек
                additional_info.clear()
                li_tags = ul_tags[1].find_all('li')
                for li_tag in li_tags:
                    additional_info.append(html_to_text(str(li_tag)))

                self._safety_add_string('temp_card', '\n'.join([x for x in additional_info if x]))

                self.main_tech = additional_info[0]
                if len(additional_info) == 2:
                    self.tech_stack = additional_info[1]

                # Парсим третий блок: домен и тип компании, локация офисов
                additional_info.clear()
                li_tags = ul_tags[2].find_all('li')
                for li_tag in li_tags:
                    additional_info.append(html_to_text(str(li_tag)))

                self._safety_add_string('temp_card', '\n'.join([x for x in additional_info if x]))

                for i, add_info in enumerate(additional_info):
                    if re.search(f"{'|'.join(patterns.domain)}", add_info):
                        self.domain = re.sub(f"{'|'.join(patterns.domain)}", '', add_info).strip()
                        additional_info[i] = ''
                    if re.search(f"{'|'.join(patterns.offices)}", add_info):
                        self.offices = re.sub(f"{'|'.join(patterns.offices)}", '', add_info).strip()
                        additional_info[i] = ''
                    if re.search(f"{'|'.join(patterns.company_type)}", add_info):
                        self.company_type = add_info
                        additional_info[i] = ''
                self._safety_add_string('notes', '\n'.join([x for x in additional_info if x]))

    def _set_parsing_status(self):
        """ Проверка результатов парсинга всех полей и установка статуса парсинга вакансии """
        # Проверка результатов парсинга полей текста сообщения Telegram
        counted_text_fields = [self.t_position, self.company, self.location, self.t_experience,
                               self.url, self.subscription]
        parsing_text_status = 'OK '
        none_count = sum(1 for item in counted_text_fields if item is None)
        if none_count:
            parsing_text_status = f'{len(counted_text_fields) - none_count} / {len(counted_text_fields)}'
        # Проверка результатов парсинга полей из HTML-кода страницы вакансии на сайте
        counted_html_fields = [self.h_position, self.description, self.lingvo, self.h_experience,
                               self.work_type, self.candidate_locations, self.main_tech, self.tech_stack,
                               self.domain, self.company_type]
        parsing_html_status = 'OK'
        if not self._is_vacancy_html_error():
            none_count = sum(1 for item in counted_html_fields if item is None)
            if none_count:
                parsing_html_status = f'{len(counted_html_fields) - none_count} / {len(counted_html_fields)}'
        self.parsing_status = f'{parsing_text_status} _ {parsing_html_status}'


class StatisticMessage(Base):  # pylint: disable=too-few-public-methods
    """ Класс-модель для сообщений со статистикой

    Attributes:
    id (Mapped[int]): идентификатор записи в БД
    message_id (Mapped[int]): идентификатор сообщения Telegram
    source (Mapped[SourceMessage]): ссылка на исходное сообщение
    vacancies_in_30d (Mapped[int]): количество вакансий за 30 дней
    candidates_online (Mapped[int]): количество кандидатов онлайн
    min_salary (Mapped[int]): минимальная заработная плата
    max_salary (Mapped[int]): максимальная заработная плата
    responses_to_vacancies (Mapped[int]): откликов на вакансию
    vacancies_per_week (Mapped[int]): количество вакансий за неделю
    candidates_per_week (Mapped[int]): количество кандидатов за неделю
    """
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
    parsing_status: Mapped[str] = mapped_column(Integer, nullable=True)

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        statistic_signs = config.message_configs.statistic.text_parsing_signs
        # Извлечение числовых значений из текста сообщения Telegram
        self._set_numeric_attr('vacancies_in_30d', statistic_signs["vacancies_in_30d"])
        self._set_numeric_attr('candidates_online', statistic_signs["candidates_online"])
        self._set_numeric_attr('responses_to_vacancies', statistic_signs["responses_to_vacancies"])
        self._set_numeric_attr('vacancies_per_week', statistic_signs["vacancies_per_week"])
        self._set_numeric_attr('candidates_per_week', statistic_signs["candidates_per_week"])
        # Извлечение информации о зарплате из текста сообщения Telegram
        self._set_salary(statistic_signs["salary"])
        for key, value in vars(self).items():
            if value == "":
                setattr(self, key, None)
        # Проверка результатов парсинга всех полей и установка статуса парсинга статистики
        self._set_parsing_status()

    def _set_numeric_attr(self, field_name: str, patterns: list):
        """ Извлечение числового значения из текста сообщения Telegram """
        if getattr(self, field_name) is not None:
            return
        pattern = f"(?:({'|'.join(patterns)}):? +)({config.re_patterns.numeric})"
        match = re.search(pattern, self.source.text)
        if match and len(match.groups()) >= 2:
            setattr(self, field_name, str_to_numeric(match.group(2)))

    def _set_salary(self, patterns: list):
        """ Извлечение информации о зарплате из текста сообщения Telegram """
        pattern = f"(?:({'|'.join(patterns)}):? +){config.re_patterns.salary_range}"
        match = re.search(pattern, self.source.text)
        if match and len(match.groups()) >= 3:
            self.min_salary = cast(int, str_to_numeric(match.group(2)))
            self.max_salary = cast(int, str_to_numeric(match.group(3)))

    def _set_parsing_status(self):
        """ Проверка результатов парсинга всех полей и установка статуса парсинга статистики """
        counted_fields = [self.vacancies_in_30d, self.candidates_online, self.min_salary, self.max_salary,
                          self.responses_to_vacancies, self.vacancies_per_week, self.candidates_per_week]
        none_count = sum(1 for item in counted_fields if item is None)
        if none_count:
            self.parsing_status = f'{len(counted_fields) - none_count} / {len(counted_fields)}'
        else:
            self.parsing_status = 'OK'


class ServiceMessage(Base):  # pylint: disable=too-few-public-methods
    """ Класс-модель для служебных сообщений

    Attributes:
    id (Mapped[int]): идентификатор записи в БД
    message_id (Mapped[int]): идентификатор сообщения Telegram
    source (Mapped[SourceMessage]): ссылка на исходное сообщение
    """
    __tablename__ = TABLE_NAMES['service']
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey(f'{TABLE_NAMES['source']}.message_id'))
    source: Mapped[SourceMessage] = relationship(back_populates='service')


def export_data_to_excel():
    """ Экспорт данных из БД в файл формата MS Excel """
    data_frames = {}
    # Импортируем данные из каждой таблицы в соответствующий DataFrame
    # и устанавливаем имена столбцов для Excel
    for key in TABLE_NAMES:
        data_frames[key] = pd.read_sql(config.export_to_excel[key].sql, engine.connect())
        data_frames[key].columns = config.export_to_excel[key].columns.values()
    # Определяем доступное имя Excel файла для экспорта
    excel_file_suffix = 1
    excel_file_name = _OUTPUT_EXCEL_FILE
    while os.path.exists(excel_file_name):
        excel_file_name = _OUTPUT_EXCEL_FILE.replace('.xlsx', f'({excel_file_suffix}).xlsx')
        excel_file_suffix += 1
    # Записываем DataFrame(s) в соответствующие листы файла Excel
    with pd.ExcelWriter(excel_file_name, engine="openpyxl") as writer:
        for key in TABLE_NAMES:
            data_frames[key].to_excel(writer, sheet_name=config.export_to_excel[key].sheet_name,
                                      index=False, header=True, freeze_panes=(1, 1))


def str_to_numeric(value: str | None) -> int | float | None:
    """ Безопасное преобразование строки в числовое значение (int или float) """
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
    """" Преобразование HTML-текста в обычный текст """
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


# Подключение к базе данных.
# Создаем соединение с базой данных и сессию
engine = create_engine('sqlite:///vacancies.db')
session = Session(engine)
# Создаем таблицы в базе данных, если они отсутствуют
Base.metadata.create_all(engine)

if __name__ == '__main__':
    pass

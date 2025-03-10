# Job Posting Parser

Скрипт для автоматизированной обработки рассылок с вакансиями в Telegram.

A script for automated parsing of job vacancy postings in Telegram.

## Описание проекта / Project Description

Проект предназначен для автоматизации обработки рассылок с вакансиями из определенных Telegram-каналов. Скрипт 
извлекает ключевую информацию из сообщений, переходит по гиперссылкам для получения полных текстов объявлений, 
производит их парсинг и сохраняет данные в базу данных для дальнейшего анализа. Решение полезно для статистического 
анализа тенденций на рынке труда, вакансий и требований к кандидатам.
 
This project is designed to automate the process of parsing job postings from Telegram channels. The script 
extracts key information from messages, follows hyperlinks to obtain full text of job announcements, retrieves 
additional vacancy details, and stores data in a database. The solution is used for statistical analysis of job 
market trends, vacancies and candidate requirements.

## Функциональность / Features

📩 Автоматический парсинг – Извлекает ключевые данные о вакансиях из сообщений в Telegram.

🔗 Переход по ссылкам – Получает полные тексты объявлений.

📊 Сохранение и анализ данных – Сохраняет информацию в базу данных SQLite для удобного доступа и анализа.

📈 Анализ рынка труда – Позволяет исследовать тенденции рынка вакансий.

Экспорт в Excel: Позволяет экспортировать данные в Excel для дальнейшей обработки.


📩 Automated Parsing – Extracts key job details from Telegram messages.

🔗 Link Following – Retrieves full job descriptions from external sources.

📊 Data Storage & Analysis – Saves extracted data into a database SQLite for easy access and analysis.

📈 Market Trend Analysis – Provides insights into job market trends and candidate requirements.

Export to Excel: Allows exporting parsed data to Excel for further processing.

## Tech Stack / Используемые технологии

Python: Core programming language.
Telethon: Library for interacting with Telegram API.
SQLAlchemy: ORM for database interactions.
AIOHTTP: Asynchronous HTTP client for fetching web content.
Pandas: Data manipulation and analysis.
BeautifulSoup: HTML parsing for extracting job details.
RE (Regular Expressions): Text pattern matching.
SQLite: Lightweight database for storing parsed data.
OpenPyXL: Excel file manipulation.
MS Excel (analysis and visualization)

Python: Основной язык программирования.
Telethon: Библиотека для работы с API Telegram.
SQLAlchemy: ORM для взаимодействия с базой данных.
AIOHTTP: Асинхронный HTTP-клиент для получения веб-контента.
Pandas: Манипуляции и анализ данных.
BeautifulSoup: Парсинг HTML для извлечения деталей вакансий.
RE (Регулярные выражения): Поиск текстовых шаблонов.
SQLite: Легковесная база данных для хранения извлеченных данных.
OpenPyXL: Работа с файлами Excel.
MS Excel (анализ и визуализация)

## Installation / Установка

1. Clone the repository:
git clone https://github.com/yourusername/job-posting-parser.git
cd job-posting-parser
2. Install the dependencies:
pip install -r requirements.txt
3. Set up your Telegram API credentials in a .env file:
Create a new application on my.telegram.org.
Add your API_ID, API_HASH and params to the .env file.
4. Run the script:
python job_posting_parser.py

1. Клонируйте репозиторий:
git clone https://github.com/yourusername/job-posting-parser.git
cd job-posting-parser
2. Настройте учетные данные API Telegram:
pip install -r requirements.txt
3. Настройте API Telegram в файле .env:
Создайте новое приложение на my.telegram.org.
Добавьте ваш API_ID, API_HASH и другие параметры в файл .env.
4. Запустите скрипт:
python job_posting_parser.py

## Usage / Использование

Run the script to start parsing job postings from Telegram channels. 
The script will automatically parse new job postings and store them in the database.

Запустите скрипт, чтобы начать парсинг вакансий из каналов Telegram.
Скрипт автоматически анализирует новые вакансии и сохраняет их в базе данных.

## Планы по развитию / Roadmap

## Лицензия / License

This project is licensed under the MIT License.

Этот проект лицензирован под MIT License.

## Автор / Author

👤 Ваше имя - GitHub - ваша-почта@example.com

Бейджи (Badges)
Статус сборки, версия, лицензия, покрытие тестами


Контакты/Авторы
Как связаться с создателями проекта


## Статус проекта (опционально)
4. Бейджи (опционально)


## Советы по написанию
- Используйте четкую иерархию заголовков
- Включайте графические элементы где возможно
- Пишите кратко, но информативно
- Регулярно обновляйте README
- Проверяйте корректность ссылок и форматирования
По мере развития проекта README следует дополнять и актуализировать, так как он служит "лицом" вашего 
- проекта и первой точкой взаимодействия с потенциальными пользователями.
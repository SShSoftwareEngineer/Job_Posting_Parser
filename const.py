INPUT_FILE = r'chat history.xlsx'

URL_TEMPLATE = 'https://djinni.co/jobs/'

SHEET_PROPERTIES = {
    'messages': {'sheet_name': 'Messages',  # Название вкладки в файле Excel
                 'col_names': ['Дата', 'ID', 'Текст сообщения', 'Признак', 'Кол-во', 'Результат'],  # Названия колонок
                 },
    'vacancy': {'sheet_name': 'Vacancies',
                'col_names': ['Дата', 'ID', 'Должность', 'Компания', 'Локация', 'Опыт', 'Зарплата', 'Текст',
                              'URL', 'Подписка', 'Заголовок', 'Доп. инф.', 'Текст'],
                },
    'statistic': {'sheet_name': 'Statistic',
                  'col_names': ['Дата', 'ID', 'Вак-ий за 30 дн.', 'Канд-ты онлайн', 'Мин. з/п', 'Макс. з/п',
                                'Откл-ов на 1 вак.', 'Вак. за нед.', 'Канд-ов за нед.'],
                  },
    'service': {'sheet_name': 'Service',
                'col_names': ['Дата', 'ID', 'Команда'],
                }
}

MESSAGE_TYPES = {
    'messages': {
        'type_str': 'Сообщения',
    },
    'vacancy': {  # Служебное название типа сообщения
        'type_str': 'Вакансии',  # Отображаемый тип сообщения
        'sign': [  # Сигнатуры для распознавания типа сообщения
            'Subscription:',
            'Подписка:'
        ],
        'detail_sign': {  # Сигнатуры для распознавания деталей сообщения
            0: [' в '],
            1: [' в '],
            2: [r', \d+ \.*', r', Без \.*', r', No \.*', r', ,\.*'],
            3: ['год опыта', 'года опыта', 'лет опыта', 'Без опыта', 'year of experience', 'years of experience',
                'No experience'],
            4: ['\$'],
            5: [],
            6: [URL_TEMPLATE],
            7: ['Подписка:', 'Subscription:'],
        }
    },
    'vacancy_parsing': {
        'type_str': 'Парсинг',
    },
    'statistic': {
        'type_str': 'Статистика',
        'sign': [
            'Статистика на Джині за запитом',
            'Статистика на Джинне по запросу',
            'Statistics on Djinni for the query'
        ],
        'detail_sign': {
            0: ['Вакансій за 30 днів:', 'Вакансий за 30 дней:', 'Job ads for 30 days:'],
            1: ['Кандидати онлайн:', 'Кандидаты онлайн:', 'Candidates online:'],
            2: ['Вилка по зарплаті:', 'Вилка по зарплате:', 'Salary range:'],
            4: ['Відгуків на одну вакансію:', 'Откликов на одну вакансию:', 'Applications per job posting:'],
            5: ['Вакансій:', 'Вакансий:', 'Jobs:'],
            6: ['Кандидатів:', 'Кандидатов:', 'Candidates:'],
        }
    },
    'service': {
        'type_str': 'Служебные',
        'sign': [
            'Активные подписки:',
            'Active Subscriptions:',
            'Поставил на паузу подписку',
            'Снял с паузы подписку',
            '/add', '/list', '/help', '/pause', '/unpause',
        ]
    },
}

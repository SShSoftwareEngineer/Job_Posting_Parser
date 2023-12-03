INPUT_FILE = r'chat history.xlsx'

SHEET_PROPERTIES = {
    'messages': {'sheet_name': 'Messages',
                 'col_names': ['Признак', 'Результат'],
                 },
    'statistic': {'sheet_name': 'Statistic',
                  'col_names': ['Дата', 'ID', 'Вак-ий за 30 дн.', 'Канд-ты онлайн', 'Мин. з/п', 'Макс. з/п',
                                'Откл-ов на 1 вак.', 'Вак. за нед.', 'Канд-ов за нед.'],
                  },
    'service': {'sheet_name': 'Service',
                'col_names': ['Command'],
                }
}

MESSAGE_TYPES = {
    'vacancy': {
        'type_str': 'Вакансии',
        'sign': [
            'Subscription:',
            'Подписка:'
        ]
    },
    'statistic': {
        'type_str': 'Статистика',
        'sign': [
            'Статистика на Джині за запитом',
            'Статистика на Джинне по запросу',
            'Statistics on Djinni for the query'
        ],
        'detail_sign': {
            ('Вакансій за 30 днів:', 'Вакансий за 30 дней:', 'Job ads for 30 days:'): 0,
            ('Кандидати онлайн:', 'Кандидаты онлайн:', 'Candidates online:'): 1,
            ('Вилка по зарплаті:', 'Вилка по зарплате:', 'Salary range:'): 2,
            ('Відгуків на одну вакансію:', 'Откликов на одну вакансию:', 'Applications per job posting:'): 4,
            ('Вакансій:', 'Вакансий:', 'Jobs:'): 5,
            ('Кандидатів:', 'Кандидатов:', 'Candidates:'): 6
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
    'messages': {
        'type_str': 'Сообщения',
    }
}

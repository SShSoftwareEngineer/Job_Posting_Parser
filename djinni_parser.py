import sys
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet import worksheet
from const import INPUT_FILE, SHEET_PROPERTIES, MESSAGE_TYPES


def create_or_clear_sheet(wb: Workbook, sheet_name: str) -> worksheet:
    if sheet_name not in wb.sheetnames:
        wb.create_sheet(sheet_name)
    else:
        wb[sheet_name].delete_rows(1, wb[sheet_name].max_row - 1)
    return wb[sheet_name]


def set_message_sign(message: str) -> str:
    mess_type = MESSAGE_TYPES.get('vacancy')
    for sign in mess_type.get('sign'):
        if sign in str(message):
            return mess_type.get('type_str')
    mess_type = MESSAGE_TYPES.get('statistic')
    for sign in mess_type.get('sign'):
        if str(message).startswith(sign):
            return mess_type.get('type_str')
    mess_type = MESSAGE_TYPES.get('service')
    for sign in mess_type.get('sign'):
        if sign in str(message):
            return mess_type.get('type_str')
    return ''


def get_detail_stat(message: str) -> list:
    result = [''] * 7
    message_parts = str(message).split('\n')
    for part in message_parts:
        for sign, index in MESSAGE_TYPES.get('statistic').get('detail_sign').items():
            for item in sign:
                if item in part:
                    if index == 2:
                        result[index], result[index + 1] = part.split('-')
                        result[index] = result[index].replace(item, '').replace('$', '').strip()
                        result[index + 1] = result[index + 1].strip()
                    else:
                        result[index] = part.replace(item, '').strip()
    for i, item in enumerate(result):
        try:
            result[i] = int(item)
        except ValueError:
            try:
                result[i] = float(item)
            except ValueError:
                result[i] = None
    return result


def main():
    wb = load_workbook(filename=INPUT_FILE)
    # Проверяем наличие листа с сообщениями
    if SHEET_PROPERTIES.get('messages').get('sheet_name') not in wb.sheetnames:
        print(f'В файле нет листа {SHEET_PROPERTIES.get("messages").get("sheet_name")}')
        sys.exit(1)
    ws_mess = wb[SHEET_PROPERTIES.get('messages').get('sheet_name')]
    # Дописываем заголовки столбцов листа с сообщениями
    ws_mess['D1'], ws_mess['E1'] = SHEET_PROPERTIES.get('messages').get('col_names')
    # Определяем тип каждого сообщения и записываем в столбец D
    report.get(MESSAGE_TYPES.get('messages').get('type_str'))[0] = ws_mess.max_row - 1
    report.get(MESSAGE_TYPES.get('messages').get('type_str'))[1] -= 1
    for row in ws_mess.rows:
        if not row[3].value:
            row[3].value = set_message_sign(row[2].value)
        if row[3].value:
            report.get(MESSAGE_TYPES.get('messages').get('type_str'))[1] += 1
    # Создаем лист со статистикой или очищаем его если он уже есть
    ws_stat = create_or_clear_sheet(wb, SHEET_PROPERTIES.get('statistic').get('sheet_name'))
    # Дописываем заголовки столбцов листа со статистикой
    for i, item in enumerate(SHEET_PROPERTIES.get('statistic').get('col_names'), 1):
        ws_stat.cell(row=1, column=i).value = item
    # Получаем детальную статистику и записываем в лист со статистикой
    detail_stat = []
    for row in ws_mess.rows:
        if row[3].value == MESSAGE_TYPES.get('statistic').get('type_str'):
            report.get(MESSAGE_TYPES.get('statistic').get('type_str'))[0] += 1
            detail_stat.extend([row[0].value, row[1].value])
            detail_stat.extend(get_detail_stat(row[2].value))
            ws_stat.append(detail_stat)
            if 'None' not in map(str, detail_stat):
                row[4].value = 'Успешно'
                report.get(MESSAGE_TYPES.get('statistic').get('type_str'))[1] += 1
            detail_stat.clear()

    wb.save(filename=INPUT_FILE)


if __name__ == '__main__':
    report = {MESSAGE_TYPES.get('messages').get('type_str'): [0, 0],
              MESSAGE_TYPES.get('vacancy').get('type_str'): [0, 0],
              MESSAGE_TYPES.get('statistic').get('type_str'): [0, 0],
              MESSAGE_TYPES.get('service').get('type_str'): [0, 0]}
    main()
    print('Отчет:')
    for key, value in report.items():
        print(f'{key}:\t{value[0]} / {value[1]}')

import const
from openpyxl import Workbook, load_workbook


def main():
    wb = load_workbook(filename=const.INPUT_FILE)
    ws = wb.active
    ws.cell(row=1, column=4, value='Признак')
    for row in ws.iter_rows(min_row=2):
        row_type = 0
        for sign in const.SERVICE_SIGN:
            if str(row[2].value).startswith(sign):
                row_type = 3
        for sign in const.STATISTIC_SIGN:
            if str(row[2].value).startswith(sign):
                row_type = 2
        for sign in const.VACANCY_SIGN:
            if sign in str(row[2].value):
                row_type = 1
        row[3].value = row_type
    wb.save(filename=const.INPUT_FILE)


if __name__ == '__main__':
    main()

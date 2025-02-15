from datetime import datetime, timedelta
def extrai_data_fechamento_de_string_yyyy_mm(date_str: str):
    year, month = map(int, date_str.split('-'))
    first_day_next_month = datetime(year + (month // 12), (month % 12) + 1, 1)
    return first_day_next_month - timedelta(days=1)
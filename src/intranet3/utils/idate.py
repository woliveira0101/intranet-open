import datetime
from dateutil.relativedelta import relativedelta

from intranet3 import helpers as h


def quarter_number(date):
    if isinstance(date, datetime.datetime):
        date = date.date
    return (date.month - 1) // 3 + 1


def next_quater(quater):
    next_q = quater + 1
    if next_q > 4:
        return 1
    else:
        return next_q


def prev_quater(quater):
    next_q = quater - 1
    if next_q < 1:
        return 4
    else:
        return next_q

first_month_of_quarter_dict = {
    1: 1,
    2: 1,
    3: 1,
    4: 4,
    5: 4,
    6: 4,
    7: 7,
    8: 7,
    9: 7,
    10: 10,
    11: 10,
    12: 10,
}


def first_day_of_quarter(date):
    return datetime.date(date.year, first_month_of_quarter_dict[date.month], 1)


def first_day_of_month(date):
    return datetime.date(date.year, date.month, 1)


def last_day_of_month(date):
    return first_day_of_month(h.next_month(date)) - relativedelta(days=1)


def months_between(d1, d2):
    result = []
    d1 = first_day_of_month(d1)
    d2 = last_day_of_month(d2)
    while d1 < d2:
        result.append(d1.month)
        d1 += relativedelta(months=1)

    return result

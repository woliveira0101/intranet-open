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

def first_day_of_week(date=None):
    if not date:
        date = datetime.date.today()
    weekday = date.weekday()
    monday = date - datetime.timedelta(days=weekday)
    if isinstance(date, datetime.datetime):
        monday = monday.date()
    return monday

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


def date_range(d1, d2, group_by_month=False):
    result = []
    if group_by_month:
        while d1 < d2:
            previous = d1
            month_result = []
            while d1.month == previous.month:
                month_result.append(d1)
                d1 += datetime.timedelta(days=1)
            result.append(month_result)
    else:
        while d1 < d2:
            result.append(d1)
            d1 += datetime.timedelta(days=1)

    return result


class xdate_range(object):
    def _gen_func(self, d1, d2, group_by_month=False):
        if group_by_month:
            while d1 < d2:
                previous = d1
                result = []
                while d1.month == previous.month:
                    result.append(d1)
                    d1 += datetime.timedelta(days=1)
                yield result
        else:
            while d1 < d2:
                yield d1
                d1 += datetime.timedelta(days=1)

    def __init__(self, d1, d2, group_by_month=False):
        self.d1 = d1
        self.d2 = d2
        self.group_by_month = group_by_month

    def __iter__(self):
        return self._gen_func(self.d1, self.d2, self.group_by_month)


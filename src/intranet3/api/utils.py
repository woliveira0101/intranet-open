# coding: utf-8
import datetime
import re


def parse_date(value):
    """
        Accepted format date:
        YYYY-MM-DD
        YYYYMMDD
    """
    pattern = re.compile(r'(?P<year>\d{4})\-*(?P<month>\d{1,2})\-*(?P<day>\d{1,2})')
    matches = pattern.match(value)

    return datetime.date(**dict((k, int(v)) for k,v in matches.groupdict().iteritems()))

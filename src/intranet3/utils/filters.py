import time
import json
from intranet3.helpers import format_time
from jinja2.exceptions import FilterArgumentError
import re

def slugify(value):
    return value.replace(' ', '-')

def parse_user_email(value):
    value = value.split('@')[0]
    return value
    #return '<br />'.join([i for i in value])

def parse_datetime_to_miliseconds(value):
    import ipdb;ipdb.set_trace()
    return int(time.mktime(value.timetuple()) * 1000)

def timedelta_to_minutes(value):
    """Sum only whole minutes"""
    return int(value.days*24*60) + int(value.seconds / 60)

def comma_number(value):
    result = round(value, 2)
    return ('%.2f' % value).replace('.', ',')


def first_words(value, amount=5):
    words = re.findall('\w+', value)[:amount]
    return ' '.join(words)

def do_dictsort(value, case_sensitive=False, by='key', attribute=None):
    """Sort a dict and yield (key, value) pairs. Because python dicts are
    unsorted you may want to use this function to order them by either
    key or value:

    .. sourcecode:: jinja

        {% for item in mydict|dictsort %}
            sort the dict by key, case insensitive

        {% for item in mydict|dicsort(true) %}
            sort the dict by key, case sensitive

        {% for item in mydict|dictsort(false, 'value') %}
            sort the dict by key, case insensitive, sorted
            normally and ordered by value.
    """
    if by == 'key':
        pos = 0
    elif by == 'value':
        pos = 1
    else:
        raise FilterArgumentError('You can only sort by either '
                                  '"key" or "value"')
    def sort_func(item):
        value = item[pos]
        if attribute:
            value = getattr(value, attribute)
        if isinstance(value, basestring) and not case_sensitive:
            value = value.lower()
        return value

    return sorted(value.items(), key=sort_func)

def tojson(dict_):
    return json.dumps(dict_)
import re
import time
import json

import markdown
from jinja2 import Markup
from jinja2.exceptions import FilterArgumentError

from intranet3 import helpers as h

format_time = h.format_time

def slugify(value):
    return value.replace(' ', '-')

def parse_user_email(value):
    value = value.split('@')[0]
    return value
    #return '<br />'.join([i for i in value])

def parse_datetime_to_miliseconds(value):
    return int(time.mktime(value.timetuple()) * 1000)

def timedelta_to_minutes(value):
    """Sum only whole minutes"""
    return int(value.days*24*60) + int(value.seconds / 60)

def comma_number(value):
    result = round(value, 2)
    return ('%.2f' % value).replace('.', ',')


def first_words(value, characters=20):
    words = re.findall('\w+', value)
    result = ' '.join(words)[:characters]
    result = '%s ...' % result
    return result

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


def is_true(value):
    return value in h.positive_values

def is_false(value):
    return value not in h.positive_values

def initials(name, letters=1):
    if ' ' in name:
        name = name.split(' ')
        first, last = name[0], name[-1]
        return '%s.%s' % (first[0].upper(), last[:letters].capitalize())
    else:
        if '@' in name:
            name = name.split('@')[0]
        # let's assume that there is first name and last name separated by non-letter character
        name = re.findall('[a-zA-Z]+', name)
        if len(name) > 1:
            first = name[0][0].upper()
            last = name[-1][:letters].capitalize()
            return '%s.%s' % (first, last)
        else:
            return name[0][:letters+1].capitalize()


def int_or_float(value):
    if value % 1:
        return '%.1f' % value
    else:
        return '%d' % value

def markdown_filter(value):
    md = markdown.Markdown()
    result = md.convert(value)
    return Markup(result)

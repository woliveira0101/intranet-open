#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
from pprint import pprint
from datetime import datetime

RE_BUG_LINK = re.compile('(http[s]?://[^\/]*/bugzilla/show_bug.cgi\?id=[\d]+)')
RE_AUTHOR_LINK = re.compile('[^<]*[<]([^>]+)[>] changed:')
RE_COMMENT_ID = re.compile('--- Comment #([\d]+) from [^<]*[<]([^>]*)[>].* ---')
RE_DEPENDENT_CHANGE = re.compile('Bug [\d]+ depends on bug [\d]+, which changed state.')


def _first(pattern, data, group=0):
    m = pattern.search(data)
    if m:
        return m.group(group)
    return ''


def parse_new_bug_mail(data):
    result = {
        'type': 'new-bug',
        ## date bieżemy z danych maila (tu zamiast tego czas obecny)
        'timestamp': datetime.now().isoformat(),
        'URL': _first(RE_BUG_LINK, data),
        'raw_data': data,
        'data': {},
        }

    params_part = False
    attachment_part = False
    content_part = False

    content = []
    param_name = None
    for line in data.split('\n'):
        l = line.strip()

        if not params_part:
            ## pierwsze wystąpienie rozpoczyna sekcję z parametrami
            if l.startswith('Summary:'):
                params_part = True

        if params_part:
            ## pusta linia kończy listę parametrów
            if len(l) == 0:
                params_part = False
                content_part = True
                continue

            ## przed dwukropkiem to nazwa parametru
            pos = 0
            if ': ' in l:
                pos = l.find(': ') + 2
                param_name = l[:pos-2]

            ## po dwukropku to treść, jeżeli brak nazwy parametru w linii
            ## to dodajemy do poprzedniego parametru
            val = l[pos:]
            if param_name in result['data']:
                val = '%s %s' % (result['data'][param_name], val)
            result['data'][param_name] = val

        if not attachment_part:
            if l.startswith('Created an attachment'):
                result['data']['attachment'] = {}
                attachment_part = True
                content_part = False
                continue

        if attachment_part:
            ## pusta linia kończy informację o załączniku
            if len(l) == 0:
                attachment_part = False
                content_part = True
                continue

            if l.startswith('--> ('):
                result['data']['attachment']['URL'] = l[5:-1]
            else:
                result['data']['attachment']['title'] = l
        
        if content_part:
            content.append(line)

    ## dodatkowe operacje
    if 'CC' in result['data']:
        val = [i.strip() for i in result['data']['CC'].split(',')]
        result['data']['CC'] = val
    
    result['data']['text'] = '\n'.join(content).strip()

    return result


def parse_bug_comment_mail(data):
    comment_id = _first(RE_COMMENT_ID, data, 1)
    url = _first(RE_BUG_LINK, data)
    if comment_id:
        url += '#' + comment_id

    author = _first(RE_AUTHOR_LINK, data, 1)
    if not author:
        author = _first(RE_COMMENT_ID, data, 2)

    if not author:
        return {}

    result = {
        'type': 'bug-comment',
        ## date bieżemy z danych maila (tu zamiast tego czas obecny)
        'timestamp': datetime.now().isoformat(),
        'URL': url,
        'author': author,
        'comment-id': comment_id,
        'raw_data': data,
        'data': {'Added': {}, 'Removed': {}},
        }

    if RE_DEPENDENT_CHANGE.search(data):
        return {}

    params_part = False
    attachment_part = False
    content_part = False

    content = []
    param_name = None
    for line in data.split('\n'):
        l = line.strip()

        if not params_part:
            ## pierwsze wystąpienie rozpoczyna sekcję z parametrami
            if l.startswith('-'*76):
                params_part = True
                continue

        if params_part:
            ## pusta linia kończy listę parametrów
            if len(l) == 0:
                params_part = False
                content_part = True
                continue

            parts = l.split('|')
            ## pierwszy człon to nazwa parametru, jeżeli pusty to wartości
            ## będą dopisywane do poprzednio napotkanego parametru
            if parts[0]:
                param_name = parts[0]

            for column_id, column_name in ((1, 'Removed'), (2, 'Added')):
                val = parts[column_id].strip()
                if val:
                    if param_name in result['data'][column_name]:
                        val = '%s %s' % (result['data'][column_name][param_name], val)

                    result['data'][column_name][param_name] = val

        if not attachment_part:
            if l.startswith('Created an attachment'):
                result['data']['attachment'] = {}
                attachment_part = True
                content_part = False
                continue

        if attachment_part:
            ## pusta linia kończy informację o załączniku
            if len(l) == 0:
                attachment_part = False
                content_part = True
                continue

            if l.startswith('--> ('):
                result['data']['attachment']['URL'] = l[5:-1]
            else:
                result['data']['attachment']['title'] = l
        
        if RE_COMMENT_ID.match(l):
            continue 

        if content_part:
            content.append(line)

    ## dodatkowe operacje
    for column_name in ('Removed', 'Added'):
        if 'CC' in result['data'][column_name]:
            val = [i.strip() for i in result['data'][column_name]['CC'].split(',')]
            result['data'][column_name]['CC'] = val
    
    result['data']['text'] = '\n'.join(content).strip()

    return result


if __name__ == '__main__':
    f = open('new-bug.txt')
    data = f.read()
    f.close()

    result = parse_new_bug_mail(data)
    pprint(result)

    for i in range(1, 5):
        f = open('bug-comment%d.txt'%i)
        data = f.read()
        f.close()

        result = parse_bug_comment_mail(data, i)
        pprint(result)

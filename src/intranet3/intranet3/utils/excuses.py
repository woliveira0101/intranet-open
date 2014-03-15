# -*- coding: utf-8 -*-
from collections import defaultdict

from intranet3.models.employees import Late
from intranet3.log import DEBUG_LOG
from intranet3.models.employees import WrongTime

DEBUG = DEBUG_LOG(__name__)

def presence():
    from sqlalchemy import desc
    lates = Late.query\
                .filter(Late.deleted==False)\
                .filter(Late.justified==True).all()

    results = defaultdict(lambda: {})
    for late in lates:
        user_id = late.user_id
        date = late.date.strftime('%Y-%m-%d')
        desc = late.explanation

        results[user_id][date] = desc

    return results

def wrongtime():
    from sqlalchemy import desc
    wrongtimes = WrongTime.query\
                          .filter(WrongTime.deleted==False)\
                          .filter(WrongTime.justified==True).all()

    results = defaultdict(lambda: {})
    for wrongtime in wrongtimes:
        user_id = wrongtime.user_id
        date = wrongtime.date.strftime('%Y-%m-%d')
        desc = wrongtime.explanation

        results[user_id][date] = desc
    return results


def presence_status(date, user_id):
    late = Late.query\
               .filter(Late.date==date)\
               .filter(Late.user_id==user_id)\
               .filter(Late.deleted==False).first()

    if not late:
        return None
    elif late.justified is None:
        return 0
    elif late.justified == True:
        return 1
    elif late.justified == False:
        return -1

def wrongtime_status(date, user_id):
    wrongtime = WrongTime.query\
                         .filter(WrongTime.date==date)\
                         .filter(WrongTime.user_id==user_id)\
                         .filter(WrongTime.deleted==False).first()

    if not wrongtime:
        return None
    elif wrongtime.justified is None:
        return 0
    elif wrongtime.justified == True:
        return 1
    elif wrongtime.justified == False:
        return -1


import calendar

from sqlalchemy import Column
from sqlalchemy.types import String, Date, Integer

from intranet3.log import DEBUG_LOG
from intranet3.models import Base, DBSession
from intranet3 import memcache

DEBUG = DEBUG_LOG(__name__)

HOLIDAYS_MEMCACHE_KEY = 'HOLIDAYS'
HOLIDAYS_MEMCACHE_TIME = 3600 * 24 #24h

class Holiday(Base):
    __tablename__ = 'holiday'
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True)
    name = Column(String, nullable=True)

    @classmethod
    def all(cls, cache=True):
        holidays = None
        if cache:
            holidays = memcache.get(HOLIDAYS_MEMCACHE_KEY)
        if holidays is None:
            holidays = dict([ (date[0], True) for date in DBSession.query(Holiday.date) ])
            memcache.set(HOLIDAYS_MEMCACHE_KEY, holidays, HOLIDAYS_MEMCACHE_TIME)
            DEBUG(u"Holidays cached")
        return holidays

    @classmethod
    def is_holiday(cls, date, holidays=None):
        if calendar.weekday(date.year, date.month, date.day) in (5, 6):
            return True
        if holidays is None:
            if cls.query.filter(cls.date==date).first():
                return True
        elif date in holidays:
                return True
        return False


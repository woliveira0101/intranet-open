import datetime
from collections import defaultdict

from sqlalchemy import Column, ForeignKey, orm
from sqlalchemy.types import String, Integer, Boolean, Date, DateTime, Text, Enum, Time

from intranet3.models import Base, DBSession, User

class Late(Base):
    __tablename__ = 'late'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    added_ts = Column(DateTime, nullable=False, default=datetime.datetime.now)
    modified_ts = Column(DateTime, nullable=False, default=datetime.datetime.now)
    date = Column(Date, nullable=False, index=True)
    explanation = Column(Text, nullable=False, index=False)
    justified = Column(Boolean, nullable=True, index=True)
    review = Column(String, nullable=True, index=True)
    deleted = Column(Boolean, nullable=False, default=False, index=True)
    late_start = Column(Time, index=True, nullable=False, default=None)
    late_end = Column(Time, index=True, nullable=False, default=None)
    work_from_home = Column(Boolean, index=False, nullable=False, default=False)


class WrongTime(Base):
    __tablename__ = 'wrong_time'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False, index=True)
    added_ts = Column(DateTime, nullable=False, default=datetime.datetime.now)
    modified_ts = Column(DateTime, nullable=False, default=datetime.datetime.now)
    date = Column(Date, nullable=False, index=True)
    explanation = Column(Text, nullable=False, index=False)
    justified = Column(Boolean, nullable=True, index=True)
    review = Column(String, nullable=True, index=True)
    deleted = Column(Boolean, nullable=False, default=False, index=True)
    user = orm.relationship("User")


class Absence(Base):
    __tablename__ = 'absence'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False, index=True)
    added_ts = Column(DateTime, nullable=False, default=datetime.datetime.now)
    modified_ts = Column(DateTime, nullable=False, default=datetime.datetime.now)
    date_start = Column(Date, nullable=False, index=True)
    date_end = Column(Date, nullable=False, index=True)
    days = Column(Integer, nullable=False, index=True)
    type = Column(Enum('planowany','zadanie','l4','okolicznosciowy', 'inne', name='absence_type_enum'), nullable=False)
    remarks = Column(Text, nullable=False, index=False)
    review = Column(String, nullable=True, index=True)
    deleted = Column(Boolean, nullable=False, default=False, index=True)
    user = orm.relationship("User")

    @property
    def pretty_type(self):
        from intranet3.forms.employees import ABSENCE_TYPES
        return dict(ABSENCE_TYPES)[self.type]

    @classmethod
    def get_for_year(cls, year):
        entries = DBSession.query('user_id', 'type', 'days').from_statement("""
            SELECT user_id, type, sum(days) as days FROM absence a
            WHERE date_part('year', a.date_start) = :year AND
                  a.deleted = false
            GROUP BY a.user_id, a.type
        """).params(year=year).all()
        result = defaultdict(lambda: 0)
        for e in entries:
            result[(e[0],e[1])] = e[2]
        return result

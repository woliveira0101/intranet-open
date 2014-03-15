import sys

from sqlalchemy.ext.declarative import declarative_base, declared_attr

from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
from intranet3.decorators import classproperty

DBSession_ = scoped_session(sessionmaker(
    extension=ZopeTransactionExtension(), expire_on_commit=False
))


class SessionWrapper(object):
    def __getattribute__(self, attr):
        return DBSession_.__getattribute__(attr)


DBSession = SessionWrapper()


class Base(object):

    @classproperty
    def query(cls):
        return DBSession_.query(cls)


Base = declarative_base(cls=Base)

from user import User, Leave
from project import Project
from client import Client
from tracker import Tracker, TrackerCredentials
from client import Client
from config import ApplicationConfig
from employees import Late, Absence, WrongTime
from holiday import Holiday
from presence import PresenceEntry
from times import TimeEntry
from sprint import Sprint, SprintBoard
from team import Team, TeamMember

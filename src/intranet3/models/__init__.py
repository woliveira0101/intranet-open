from sqlalchemy.ext.declarative import declarative_base, declared_attr

from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
from intranet3.decorators import classproperty

DBSession = scoped_session(sessionmaker(
    extension=ZopeTransactionExtension(), expire_on_commit=False
))


class Base(object):

    @classproperty
    def query(cls):
        return DBSession.query(cls)

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
from sprint import Sprint
from team import Team, TeamMember

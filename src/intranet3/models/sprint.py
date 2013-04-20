import datetime

from sqlalchemy.types import String, Integer, Date, DateTime, Text, Float
from sqlalchemy import Column, ForeignKey

from intranet3.models import Base
from intranet3.log import WARN_LOG, INFO_LOG, DEBUG_LOG

LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
WARN = WARN_LOG(__name__)

class Sprint(Base):
    __tablename__ = 'sprint'

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    client_id = Column(Integer, ForeignKey('client.id'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False, index=True)
    start = Column(Date, nullable=False)
    end = Column(Date, nullable=False)

    goal = Column(Text, nullable=False, default='')

    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    modified = Column(DateTime, nullable=False, default=datetime.datetime.now)

    commited_points = Column(Integer, nullable=False, default=0)
    achieved_points = Column(Integer, nullable=False, default=0)
    worked_hours = Column(Float, nullable=False, default=0.0)

    @property
    def velocity(self):
        return self.achieved_points / self.worked_hours if self.worked_hours else 0.0


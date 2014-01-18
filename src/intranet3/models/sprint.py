import json
import datetime

from sqlalchemy.types import String, Integer, Date, DateTime, Text, Float
from sqlalchemy import Column, ForeignKey, orm
from sqlalchemy.dialects import postgresql

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
    bugs_project_ids = Column(postgresql.ARRAY(Integer))
    start = Column(Date, nullable=False)
    end = Column(Date, nullable=False)

    goal = Column(Text, nullable=False, default='')

    created = Column(DateTime, nullable=False, default=datetime.datetime.now)
    modified = Column(DateTime, nullable=False, default=datetime.datetime.now)

    commited_points = Column(Integer, nullable=False, default=0)
    achieved_points = Column(Integer, nullable=False, default=0)
    worked_hours = Column(Float, nullable=False, default=0.0)
    bugs_worked_hours = Column(Float, nullable=False, default=0.0)

    retrospective_note = Column(Text, nullable=False, default='')
    board = Column(Text, nullable=False, default='')

    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True, index=True)
    team = orm.relationship('Team')

    def get_board(self):
        return json.loads(self.board)

    @property
    def velocity(self):
        return (self.achieved_points / self.worked_hours * 8.0) if self.worked_hours else 0.0

    @property
    def user_stories_velocity(self):
        return (self.achieved_points / self.bugs_worked_hours * 8.0) if self.bugs_worked_hours else 0.0

    def calculate_velocities(self, associated_sprints):
        worked_hours_sum = sum([s[1] for s in associated_sprints])
        bugs_worked_hours_sum = sum([s[2] for s in associated_sprints])
        anchieved_points_sum = sum([s[3] for s in associated_sprints])

        self.mean_velocity = 8.0 * anchieved_points_sum / worked_hours_sum \
            if worked_hours_sum else 0.0

        self.mean_bugs_velocity = 8.0 * anchieved_points_sum / bugs_worked_hours_sum \
            if bugs_worked_hours_sum else 0.0


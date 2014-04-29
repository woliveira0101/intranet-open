import json
import datetime

from sqlalchemy.types import String, Integer, Date, DateTime, Text, Float
from sqlalchemy import Column, ForeignKey, orm
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import UniqueConstraint

from intranet3.models import (
    Base,
    DBSession,
)
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

    velocity = Column(Float, nullable=False, default=0.0)
    velocity_mean = Column(Float, nullable=False, default=0.0)
    story_velocity = Column(Float, nullable=False, default=0.0)
    story_velocity_mean = Column(Float, nullable=False, default=0.0)

    team_id = Column(Integer, ForeignKey('teams.id'), nullable=True, index=True)
    team = orm.relationship('Team')

    def get_board(self):
        if self.board:
            return json.loads(self.board)

        return [
            {
                'name': 'TODO',
                'sections': [
                    {
                        'name': '',
                        "cond": ''
                    }
                ]
            }
        ]

    def calculate_velocities(self):
        self.velocity = \
            8.0 * self.achieved_points / self.worked_hours \
            if self.worked_hours else 0.0

        self.story_velocity = \
            8.0 * self.achieved_points / self.bugs_worked_hours \
            if self.bugs_worked_hours else 0.0

        sprint_velocities = DBSession.query(
            Sprint.velocity,
            Sprint.story_velocity,
        ).filter(Sprint.project_id == self.project_id) \
            .filter(Sprint.id != self.id) \
            .all()

        sprint_velocities.append((self.velocity, self.story_velocity))

        velocities, story_velocities = zip(*sprint_velocities)

        self.velocity_mean = float(sum(velocities)) / len(velocities)

        self.story_velocity_mean = \
            float(sum(story_velocities)) / len(story_velocities)

        DBSession.add(self)


class SprintBoard(Base):
    __tablename__ = 'sprint_board'

    id = Column(Integer, primary_key=True, index=True)
    board = Column(Text, nullable=False)
    name = Column(Text, nullable=False)

    user_id = Column(Integer, ForeignKey('user.id'), index=True)
    user = orm.relationship('User')

    __table_args__ = (UniqueConstraint('name', 'user_id', name='board_name_user_id_unique'), {})

    def to_dict(self):
        return dict(
            id=self.id,
            board=self.board,
            name=self.name,
            user=self.user.to_dict(),
        )

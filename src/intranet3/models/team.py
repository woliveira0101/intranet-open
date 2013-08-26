# -*- coding: utf-8 -*-
from sqlalchemy import Column, ForeignKey, orm
from sqlalchemy.types import Integer, String
from sqlalchemy.schema import UniqueConstraint

from intranet3.models import Base, User

class Team(Base):
    __tablename__ = 'teams'
    
    id = Column(Integer, primary_key=True, nullable=False, index=True)
    name = Column(String(255), unique=True, nullable=False)
    team_members = orm.relationship('TeamMember', backref='team', lazy='dynamic')

    @property
    def avatar_url(self):
        return '/thumbs/team/%s' % self.id

    @property
    def users(self):
        return [tm.user_id for tm in self.team_members]
    
    def to_dict(self):
        team_dict = {
            'id': self.id,
            'name': self.name,
            'users': self.users,
            'img': self.avatar_url,
        }
            
        return team_dict
    
    
class TeamMember(Base):
    __tablename__ = 'team_members'
    
    id = Column(Integer, nullable=False, index=True, primary_key=True)
    team_id = Column(Integer, ForeignKey('teams.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    
    __table_args__ = (UniqueConstraint('team_id', 'user_id', name='team_members_team_id_user_id_unique'), {})

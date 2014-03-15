import datetime

from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import DateTime, Date, String, Integer, Float, Boolean

from intranet3.models import Base


class TimeEntry(Base):
    __tablename__ = 'time_entry'
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    time = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    
    added_ts = Column(DateTime, nullable=False, default=datetime.datetime.now)
    modified_ts = Column(DateTime, nullable=False, default=datetime.datetime.now)
    
    timer_ts = Column(DateTime)
    
    ticket_id = Column(Integer, nullable=True, index=True)
    
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False, index=True)
    # TODO: task
    deleted = Column(Boolean, nullable=False, default=False, index=True)
    frozen = Column(Boolean, nullable=False, default=False, index=True)
    
    def to_dict(self):
        entry = {
            'id': self.id,
            'desc': self.description,
            'added': self.added_ts.strftime("%d.%m.%Y"),
            'modified': self.modified_ts.strftime("%d.%m.%Y"),
            'ticket_id': self.ticket_id,
            'time': self.time,
            'project': None
        }

        if self.project:
            entry.update({
                'project': {
                    'client_name': self.project.client.name,
                    'project_name': self.project.name,
                }
            })
        return entry

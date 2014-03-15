import datetime

from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import DateTime, String, Integer, Boolean

from intranet3.models import Base

class PresenceEntry(Base):
    __tablename__ = 'presence_entry'
    
    id = Column(Integer, primary_key=True)
    
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    ts = Column(DateTime, nullable=False, default=datetime.datetime.now, index=True)
    url = Column(String, nullable=False)
    processed = Column(Boolean, default=False, nullable=False, index=True)
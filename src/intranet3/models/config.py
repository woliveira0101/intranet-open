import datetime

from sqlalchemy import Column
from sqlalchemy.types import DateTime, String, Integer
from sqlalchemy.schema import ForeignKey
from sqlalchemy.dialects import postgresql

from intranet3 import memcache
from intranet3.utils.encryption import encrypt, decrypt
from intranet3.models import Base, DBSession, Project, User
from intranet3.log import DEBUG_LOG

DEBUG = DEBUG_LOG(__name__)
OFFICE_IP_MEMCACHE_KEY = 'OFFICE_IP'


class ApplicationConfig(Base):
    """ Global application configuration """
    # password used to enrypt all other sensitive information
    __tablename__ = 'application_config'
    
    id = Column(Integer, primary_key=True)
    
    date = Column(DateTime, default=datetime.datetime.now, nullable=False, index=True)
    office_ip = Column(String, nullable=False)
    
    google_user_email = Column(String, nullable=False)
    google_user_password = Column(String, nullable=False)
    holidays_spreadsheet = Column(String, nullable=False)


    hours_employee_project = Column(String, nullable=False)
    absence_project_id = Column(Integer, ForeignKey(Project.id), nullable=True)
    reports_project_ids = Column(postgresql.ARRAY(Integer))
    reports_omit_user_ids = Column(postgresql.ARRAY(Integer))
    reports_without_ticket_project_ids = Column(postgresql.ARRAY(Integer))
    reports_without_ticket_omit_user_ids = Column(postgresql.ARRAY(Integer))
    freelancers = Column(String, nullable=True)
    hours_ticket_user_id = Column(Integer, ForeignKey(User.id), nullable=True)
    cleaning_time_presence = Column(Integer, default=7, nullable=False)
    monthly_late_limit = Column(Integer, default=3, nullable=False)
    monthly_incorrect_time_record_limit = Column(Integer, default=3, nullable=False)

    @classmethod
    def get_current_config(cls, allow_empty=False):
        """
        @rtype: ApplicationConfig
        """
        config = DBSession().query(cls).first()
        if config is not None:
            return config
        elif allow_empty:
            return None
        else:
            raise ValueError(u"Application config not found")
        
    def get_freelancers(self):
        return [value.strip() for value in self.freelancers.split(u'\n')] if self.freelancers else []

    @classmethod
    def get_office_ip(cls):
        office_ip = memcache.get(OFFICE_IP_MEMCACHE_KEY)
        if not office_ip:
            config = cls.get_current_config(allow_empty=True)
            if config is None:
                return
            office_ip = [c.strip() for c in config.office_ip.split(',')]
            memcache.set(OFFICE_IP_MEMCACHE_KEY, office_ip)
        return office_ip

    def __getattribute__(self, name):
        value = super(ApplicationConfig, self).__getattribute__(name)
        if name == 'google_user_password' and value:
            value = decrypt(value)
        return value

    def __setattr__(self, name, value):
        if name == 'google_user_password' and value:
            value = encrypt(value)
        super(ApplicationConfig, self).__setattr__(name, value)


    def invalidate_office_ip(self):
        """ invalidates the cached value of office IP """
        memcache.delete(OFFICE_IP_MEMCACHE_KEY)
        DEBUG(u"Office IP invalidated")


from pyramid.decorator import reify
from sqlalchemy import Column, ForeignKey, orm, distinct
from sqlalchemy.types import String, Integer

from intranet3.models import Base, User, DBSession, Project

class Client(Base):
    __tablename__ = 'client'

    id = Column(Integer, primary_key=True, index=True)
    coordinator_id = Column(Integer, ForeignKey(User.id), nullable=True, index=True)
    name = Column(String, unique=True, nullable=False)
    emails = Column(String, nullable=True)

    color = Column(String, nullable=False, default='')
    google_card = Column(String, nullable=True)
    google_wiki = Column(String, nullable=True)
    selector    = Column(String, nullable=True) 
    street      = Column(String, nullable=True)
    city        = Column(String, nullable=True)
    postcode    = Column(String, nullable=True)
    nip         = Column(String, nullable=True)
    mailing_url = Column(String, nullable=True)
    wiki_url    = Column(String, nullable=True)
    note        = Column(String, nullable=True)

    projects = orm.relationship('Project', backref='client', lazy='dynamic')
    coordinator = orm.relationship('User', backref='client')

    @reify
    def active(self):
        return self.has_active_project()

    def has_active_project(self):
        from intranet3.models import Project
        result = DBSession.query(Project.id)\
                       .filter(Project.active==True)\
                       .filter(Project.client_id==self.id).limit(1).first()
        return bool(result)

    @classmethod
    def get_emails(cls):
        emails_cols = DBSession.query(distinct(Client.emails))\
                               .filter(Project.client_id==Client.id)\
                               .filter(Project.active==True).all()
        emails = []
        for emails_str in emails_cols:
            if emails_str[0]:
                emails.extend([ email.strip() for email in emails_str[0].split('\n') if '@' in email ])

        return emails



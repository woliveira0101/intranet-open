# -*- coding: utf-8 -*-
import datetime
import requests
from collections import defaultdict

from pyramid.decorator import reify
from sqlalchemy import Column, ForeignKey, orm, or_
from sqlalchemy.types import String, Boolean, Integer, Date, Enum, Text
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.expression import exists

from intranet3 import memcache, config
from intranet3.log import ERROR_LOG
from intranet3.models import Base, DBSession


ERROR = ERROR_LOG(__name__)
INFO = ERROR_LOG(__name__)

GOOGLE_ACCESS_TOKEN_MEMCACHE_KEY = 'google-access-token-userid-%s'

levels = [
    ('1', 'INTERN'),
    ('2', 'P1'),
    ('4', 'P2'),
    ('8', 'P3'),
    ('16', 'P4'),
    ('32', 'FED'),
    ('64', 'ADMIN'),
    ('128', 'Expert zew.'),
    ('256', 'Android Dev'),
    ('512', 'Tester'),
    ('1024', 'CEO\'s Assistant'),
    ('2048', 'CEO'),
]


class User(Base):
    __tablename__ = 'user'
    LOCATIONS = {'poznan': (u'Poznań', 'P'), 'wroclaw': (u'Wrocław', 'W')}

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    admin = Column(Boolean, default=False, nullable=False)
    freelancer = Column(Boolean, default=False, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_programmer = Column(Boolean, default=False, nullable=False)
    is_frontend_developer = Column(Boolean, default=False, nullable=False)
    is_graphic_designer = Column(Boolean, default=False, nullable=False)
    levels = Column(Integer, nullable=False, default=0)

    availability_link = Column(String, nullable=True, default=None)
    tasks_link = Column(String, nullable=True, default=None)
    skype = Column(String, nullable=True, default=None)
    irc = Column(String, nullable=True, default=None)
    phone = Column(String, nullable=True, default=None)
    phone_on_desk = Column(String, nullable=True, default=None)
    location = Column(
        Enum(*LOCATIONS.keys(), name='user_location_enum'), nullable=True,
        default='poznan',
    )

    start_work = Column(
        Date, nullable=False,
        default=lambda: datetime.date.today() + datetime.timedelta(days=365 * 30),
    )
    start_full_time_work = Column(
        Date, nullable=False,
        default=lambda: datetime.date.today() + datetime.timedelta(days=365 * 30),
    )
    description = Column(String, nullable=True, default=None)

    presences = orm.relationship('PresenceEntry', backref='user', lazy='dynamic')
    credentials = orm.relationship('TrackerCredentials', backref='user', lazy='dynamic')
    time_entries = orm.relationship('TimeEntry', backref='user', lazy='dynamic')
    coordinated_projects = orm.relationship('Project', backref='coordinator', lazy='dynamic')
    leaves = orm.relationship('Leave', backref='user', lazy='dynamic')
    lates = orm.relationship('Late', backref='user', lazy='dynamic')

    groups = Column(postgresql.ARRAY(String))

    refresh_token = Column(String, nullable=False)
    _access_token = None

    @property
    def user_groups(self):
        return ", ".join([group for group in self.groups])

    @reify
    def access_token(self):
        access_token = memcache.get(GOOGLE_ACCESS_TOKEN_MEMCACHE_KEY % self.id)
        if access_token:
            INFO('Found access token %s for user %s' % (
                access_token, self.name
            ))
        if not access_token:
            args = dict(
                client_id=config['GOOGLE_CLIENT_ID'],
                client_secret=config['GOOGLE_CLIENT_SECRET'],
                refresh_token=self.refresh_token,
                grant_type='refresh_token',
            )
            response = requests.post('https://accounts.google.com/o/oauth2/token', data=args, verify=False)
            if 'access_token' not in response.json:
                ERROR('There is no token in google response %s, status_code: %s, refresh_token: %s, user.email: %s' % (response.json, response.status_code, self.refresh_token, self.email))
                return None

            data = response.json
            INFO('Received response with access_token for user %s: %s' % (
                self.name, data
            ))
            access_token = data['access_token']
            expires = data['expires_in']
            expires = int(expires / 2)
            INFO('Saving access_token %s for user %s in memcached for %s s' % (
                access_token, self.name, expires,
            ))
            memcache.set(
                GOOGLE_ACCESS_TOKEN_MEMCACHE_KEY % self.id,
                access_token,
                expires
            )

        return access_token

    def get_leave(self, year):
        leave = Leave.query.filter(Leave.user_id==self.id).filter(Leave.year==year).first()
        if leave:
            return leave.number
        else:
            return 0

    @reify
    def is_coordinator(self):
        ## circular import :/
        from intranet3.models import Project, Client
        is_coordinator = DBSession.query(exists().where(or_(
            Client.coordinator_id==self.id,
            Project.coordinator_id==self.id
        ))).scalar()
        return is_coordinator

    @property
    def avatar_url(self):
        return '/api/images/users/%s' % self.id

    def get_location(self, short=False):
        if short:
            return self.LOCATIONS[self.location][1]
        else:
            return self.LOCATIONS[self.location][0]
    
    @property
    def levels_list(self):
        l = []
        i = 1
        while i <= self.levels:
            if self.levels & i:
                l.append(i)
            i=i * 2
        return l
    
    @property
    def levels_html(self):
        if not self.levels:
            return ''

        l = []
        for mask,label in levels:
            if self.levels & int(mask):
                l.append(label)
        return ', '.join(l)

    def get_client(self):
        from intranet3.models import Client
        email = self.email
        client = Client.query.filter(Client.emails.contains(email)).first() or None
        return client

    @reify
    def client(self):
        return self.get_client()

    @classmethod
    def is_not_client(cls):
        # used in queries i.e. User.query.filter(User.is_not_client()).filter(...
        # <@ = http://www.postgresql.org/docs/8.3/static/functions-array.html
        return User.groups.op('<@')('{user, admin, scrum}')

    @classmethod
    def is_client(cls):
        # used in queries i.e. User.query.filter(User.is_client()).filter(...
        # <@ = http://www.postgresql.org/docs/8.3/static/functions-array.html
        return User.groups.op('<@')('{client}')


class Leave(Base):
    __tablename__ = 'leave'
    id = Column(Integer, primary_key=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    number = Column(Integer, nullable=False)
    remarks = Column(Text, nullable=False, index=False)

    __table_args__ = (UniqueConstraint('user_id', 'year', name='_user_year_uc'), {})

    @classmethod
    def get_for_year(cls, year):
        leaves = Leave.query.filter(Leave.year==year).all()
        result = defaultdict(lambda: (0, u''))
        for leave in leaves:
            result[leave.user_id] = (leave.number, leave.remarks)
        return result

    @classmethod
    def get_used_for_year(cls, year):
        used_entries = DBSession.query('user_id', 'days').from_statement("""
            SELECT t.user_id, sum(t.time)/8 as days
            FROM time_entry t
            WHERE deleted = false AND
                  t.project_id = 86 AND
                  date_part('year', t.date) = :year
            GROUP BY user_id
        """).params(year=year).all()
        used = defaultdict(lambda: 0)
        for u in used_entries:
            used[u[0]] = int(u[1])
        return used

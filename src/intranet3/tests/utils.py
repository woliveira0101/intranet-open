import os
import unittest
import mock
from pyramid import testing

from sqlalchemy.orm import sessionmaker
from sqlalchemy import engine_from_config
from paste.deploy.loadwsgi import appconfig

from mockups import MockUpsMixin

from intranet3 import models



class BaseTestCase(MockUpsMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        here = os.path.dirname(__file__)
        settings = appconfig(
            'config:' + os.path.join(here, '../../../parts/etc/', 'test.ini')
        )
        cls.engine = engine_from_config(settings, prefix='sqlalchemy.')
        cls.Session = sessionmaker()

    def setUp(self):
        connection = self.engine.connect()

        # begin a non-ORM transaction
        self.trans = connection.begin()

        # bind an individual Session to the connection
        self.session = self.Session(bind=connection)

        models.DBSession = self.session

        memcached_mock = mock.Mock()

        memcached_mock.get.return_value = None
        memcached_mock.set.return_value = None
        self.memcached_mock = memcached_mock

    def tearDown(self):
        # rollback - everything that happened with the
        # Session above (including calls to commit())
        # is rolled back.
        testing.tearDown()
        self.trans.rollback()
        self.session.close()
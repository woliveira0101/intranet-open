from os.path import (
    dirname,
    join,
    isfile,
)
import unittest

from webtest import TestApp
from mock import patch

from sqlalchemy import engine_from_config
from sqlalchemy.orm.session import Session
from pyramid.security import has_permission
from pyramid import (
    paster,
    testing,
)

import intranet3

ROOT_PATH = dirname(__file__)
setting_file = join(ROOT_PATH, "../../../parts/etc/", "test.ini")

# creating memcache before other modules are loaded :(
if isfile(setting_file):
    settings = paster.get_appsettings(setting_file)
    intranet3.init_memcache(settings)
else:
    settings = None

from intranet3 import models as intranet_models
from intranet3.testing import mocks
from intranet3.testing.factory import FactoryMixin

connection = None
engine = None
app = None


def setup_module():
    global connection, app, engine
    if settings is None:
        raise Exception('Settings file not found %s' % setting_file)

    engine = engine_from_config(settings, prefix='sqlalchemy.')

    connection = engine.connect()
    intranet_models.Base.metadata.drop_all(engine)

    intranet_models.DBSession.configure(bind=engine)
    intranet_models.Base.metadata.create_all(engine)

    app = TestApp(paster.get_app(setting_file))


def teardown_module():
    global connection, engine

    intranet_models.Base.metadata.drop_all(engine)
    connection.close()


class IntranetBaseTest(unittest.TestCase):

    def setUp(self):
        self._transaction = connection.begin()
        intranet_models.DBSession_ = Session(connection)
        intranet3.memcache.clear()

    def tearDown(self):
        intranet_models.DBSession_.close()
        self._transaction.rollback()


class IntranetTest(IntranetBaseTest):

    def setUp(self):
        super(IntranetTest, self).setUp()
        self.config = testing.setUp()

        self.request = Request()
        self.request.user = intranet_models.User()

    def tearDown(self):
        super(IntranetTest, self).tearDown()
        testing.tearDown()


class IntranetWebTest(IntranetBaseTest):

    def tearDown(self):
        super(IntranetWebTest, self).tearDown()
        app.reset()

    def get(self, *args, **kwargs):
        return app.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return app.post(*args, **kwargs)

    def post_json(self, *args, **kwargs):
        return app.post_json(*args, **kwargs)

    def put(self, *args, **kwargs):
        return app.put(*args, **kwargs)

    def put_json(self, *args, **kwargs):
        return app.put_json(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return app.delete(*args, **kwargs)

    def delete_json(self, *args, **kwargs):
        return app.delete_json(*args, **kwargs)

    def login(self, name, email):
        with patch("intranet3.views.auth.requests.get") as request_get:
            request_get.return_value = mocks.request_get(name, email)
            with patch(
                "intranet3.views.auth.OAuth2WebServerFlow.step2_exchange"
            ) as flow:
                flow.return_value = mocks.MockOAuth2FlowSampleData()
                with patch("intranet3.views.auth.ApplicationConfig") as config:
                    config.return_value = mocks.MockApplicationConfig()
                    app.get('/auth/callback')


class Request(testing.DummyRequest):

    def __init__(self):
        self.tmpl_ctx = {}

        super(Request, self).__init__()

    def has_perm(self, perm):
        return has_permission(perm, self.context, self)

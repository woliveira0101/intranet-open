import string
import random
from intranet3.models import *


class MockUpsMixin(object):

    def _rand_name(self):
        return ''.join(random.choice(string.letters + string.digits) for i in xrange(10))

    def mock_user(self):
        user = User(
            email='%s@o2.pl' % self._rand_name(),
            name=self._rand_name(),
            location='poznan',
            refresh_token='a',
        )
        user.groups = []
        self.session.add(user)
        self.session.flush()
        return user

    def mock_admin(self):
        user = self.mock_user()
        user.groups = ['admin']
        self.session.add(user)
        self.session.flush()
        return user


    def mock_client(
            self,
            coordinator_id=None,
            name=None):

        if not name:
            name = self._rand_name()

        kwargs = locals().copy()
        kwargs.pop('self')

        client = Client(**kwargs)

        self.session.add(client)
        self.session.flush()
        return client

    def mock_tracker(
            self,
            type='bugzilla',
            name=None,
            url=None):

        if not name:
            name = self._rand_name()
        if not url:
            url = 'http://%s.com' % self._rand_name()

        kwargs = locals().copy()
        kwargs.pop('self')

        tracker = Tracker(**kwargs)
        self.session.add(tracker)
        self.session.flush()
        return tracker

    def mock_project(
            self,
            name=None,
            client_id=None,
            tracker_id=None,
            active=True,
            project_selector=None,
            component_selector=None,
            version_selector=None,
            turn_off_selectors=False):

        if not name:
            name = self._rand_name()

        kwargs = locals().copy()
        kwargs.pop('self')

        if not client_id:
            client = self.mock_client()
            kwargs['client_id'] = client.id

        if not tracker_id:
            tracker = self.mock_tracker()
            kwargs['tracker_id'] = tracker.id

        p = Project(**kwargs)
        self.session.add(p)
        self.session.flush()
        return p

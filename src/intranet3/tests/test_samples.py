'''
Module with some example test cases. It does not test any particular feature,
it's just a showcase of our testing framework. It also ensures that
transactions work as they should.
Can be deleted in the future.
'''

from intranet3.tests import (
    IntranetTest,
    IntranetWebTest,
    FactoryMixin,
)
from intranet3.api.presence import PresenceApi
from intranet3 import models


class SampleTestCase(FactoryMixin, IntranetTest):

    def test_create_sth(self):
        self.create_users(name='Bolek')

        users = models.User.query.all()

        self.assertEqual(len(users), 1)
        self.assertEquals(users[0].name, 'Bolek')

    def test_query_sth(self):
        users = models.User.query.all()
        self.assertEqual(len(users), 0)

    def test_get_absences(self):
        data = PresenceApi(self.request.context, self.request)()
        self.assertEqual(len(data['lates']), 0)


class SampleWebTestCase(IntranetWebTest):

    def test_get_absences(self):
        self.login('asd', 'asd@stxnext.pl')
        self.get('/api/presence', status=200)

    def test_get_absences_json(self):
        self.login('asd', 'asd@stxnext.pl')
        data = self.get('/api/presence').json
        self.assertEquals(len(data['lates']), 0)

    def test_get_user(self):
        users = models.User.query.all()
        self.assertEquals(len(users), 0)

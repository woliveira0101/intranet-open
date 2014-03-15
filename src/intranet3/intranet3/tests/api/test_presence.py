from datetime import datetime

from intranet3.testing import (
    IntranetWebTest,
    FactoryMixin,
)
from intranet3 import models


class PresenceApiTestCase(FactoryMixin, IntranetWebTest):

    def create_late(self, user, date):
        late = models.Late(
            user_id=user.id,
            date=date,
            explanation='explanation',
            justified=None,
            late_start=datetime.time(date),
            late_end=datetime.time(date),
            work_from_home=False,
        )

        models.DBSession.add(late)

    def test_not_logged_in(self):
        self.get('/api/presence', status=302)

    def test_get_absences(self):
        # TODO Bug detected, presence api fails if date is given because of
        # malformed memcache key. Fix the bug.

        date = datetime(2014, 1, 1)

        user = self.create_user()
        self.create_late(user, date)

        self.login('asd', 'asd@stxnext.pl')
        data = self.get(
            '/api/presence',
            params={'date': date.strftime('%d.%m.%Y')},
            status=200
        ).json

        self.assertEquals(len(data['lates']), 1)
        self.assertEquals(data['lates'][0]['explanation'], 'explanation')

        self.assertEquals(len(data['absences']), 0)
        self.assertEquals(len(data['blacklist']), 0)

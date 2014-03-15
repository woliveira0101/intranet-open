import mock

from intranet3.utils.mail_fetcher import MailCheckerTask

from .mailfetcher_fixtures import POPMock
from intranet3.testing import FactoryMixin, IntranetTest
from intranet3 import models as m



class MailFetcherTest(FactoryMixin, IntranetTest):

    def create_all(self):
        tracker = self.create_tracker()
        user = self.create_user()
        client = self.create_client()
        project = self.create_project(
            tracker=tracker,
            client=client,
            project_selector='PRODUCT_X',
            component_selector='COMPONENT_X',
        )
        self.add_creds(user, tracker, 'userx')

        return user, tracker, client, project


    @mock.patch('intranet3.utils.mail_fetcher.transaction')
    def test_mail(self, transaction):
        user, tracker, client, project = self.create_all()

        popmock = POPMock(5)
        with popmock:
            MailCheckerTask()()
        m.DBSession.flush()

        timeentries = m.DBSession.query(m.TimeEntry).all()
        self.assertEqual(len(timeentries), 5)
        for t in timeentries:
            self.assertEqual(t.user_id, user.id)
            self.assertEqual(t.project_id, project.id)
            self.assertEqual(t.time, 0.1)

        with popmock:
            MailCheckerTask()()
        m.DBSession.flush()

        timeentries = m.DBSession.query(m.TimeEntry).all()
        self.assertEqual(len(timeentries), 5)
        for t in timeentries:
            self.assertEqual(t.user_id, user.id)
            self.assertEqual(t.project_id, project.id)
            self.assertEqual(t.time, 0.2)

# coding: utf-8

from pyramid import testing

from intranet3.testing import (
    IntranetTest,
    FactoryMixin,
)
from intranet3.api.times import TimeCollection


class BugViewTestCase(FactoryMixin, IntranetTest):
    def test_time_view(self):
        user = self.create_user(groups=[])
        self.request.method = "GET"
        self.request.user = user
        self.request.context = testing.DummyResource()

        TimeCollection(self.request.context, self.request)()

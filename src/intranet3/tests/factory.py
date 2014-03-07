from intranet3 import models


class FactoryMixin(object):
    # Current state of counter
    cid = 1  # Client
    uid = 1  # User
    pid = 1  # Project
    tid = 1  # Tracker

    def create_user(
        self,
        name="",
        domain="stxnext.pl",
        groups=[],
        **kwargs
    ):
        username = name or "user_%s" % self.uid
        user = models.User(
            email="%s@%s" % (username, domain),
            name=username,
            location="wroclaw",
            refresh_token='test_token',
            **kwargs
        )
        user.groups = groups
        models.DBSession.add(user)
        models.DBSession.flush()
        if name == "":
            self.uid += 1
        return user

    def create_users(
        self,
        amount=1,
        domain="stxnext.pl",
        groups=[],
        **kwargs
    ):
        return [
            self.create_user(
                domain=domain,
                groups=groups,
                **kwargs
            )
            for i in xrange(0, amount)
        ]

    def create_client(self, name="", user=None, **kwargs):
        if user is None:
            user = self.create_user(groups=['user'])
        client = models.Client(
            coordinator_id=user.id,
            name="client_%s" % self.cid,
            color="red?",
            emails="blabla@gmail.com",
            **kwargs
        )
        models.DBSession.add(client)
        models.DBSession.flush()
        self.cid += 1
        return client

    def create_tracker(self, name="", **kwargs):
        name = name or "tracker_%s" % self.tid
        tracker = models.Tracker(
            type="bugzilla",
            name=name,
            url="http://%s.name" % name,
            **kwargs
        )
        models.DBSession.add(tracker)
        models.DBSession.flush()
        self.tid += 1
        return tracker

    def create_project(
        self,
        name='test project',
        user=None,
        client=None,
        tracker=None,
        **kwargs
    ):
        if user is None:
            user = self.create_user()
        if client is None:
            client = self.create_client()
        if tracker is None:
            tracker = self.create_tracker()
        name = name or "project_%s" % self.pid
        project = models.Project(
            name=name,
            coordinator_id=user.id,
            client_id=client.id,
            tracker_id=tracker.id,
            active=True,
            **kwargs
        )
        models.DBSession.add(project)
        models.DBSession.flush()
        self.pid += 1
        return project

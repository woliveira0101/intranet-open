class Scrum(object):
    def __init__(self, bug):
        self.__bug = bug

    @property
    def points(self):
        return None

    @property
    def velocity(self):
        return 0.0


class Bug(object):
    Scrum = Scrum

    def __init__(self, tracker, login_mapping, raw_data):
        # we shouldn't keep login_mapping inside Bug object
        # we do not need it to be pickled during memcached set
        self.tracker = tracker
        self.data = self.parse(raw_data)
        self.owner = self.__resolve_user(
            self.get_owner(self.data),
            login_mapping,
            )
        self.reporter = self.__resolve_user(
            self.get_reporter(self.data),
            login_mapping,
            )
        self.scrum = self.Scrum(self)

    def __resolve_user(self, orig_login, login_mapping):
        return login_mapping.get(
            orig_login.lower(),
            User(name=orig_login, email=orig_login),
            )

    def parse(self, raw_data):
        return raw_data

    def get_owner(self, data):
        """ Get tracker owner username """
        return None

    def get_reporter(self, data):
        """ Get tracker reporter username """
        return None

    @property
    def id(self):
        return None

    @property
    def desc(self):
        return None

    @property
    def priority(self):
        return None

    @property
    def severity(self):
        return None

    @property
    def status(self):
        return None

    @property
    def resolution(self):
        return None

    @property
    def url(self):
        return None

    @property
    def project(self):
        return None

    @property
    def opendate(self):
        return None

    @property
    def changeddate(self):
        return None

    @property
    def dependson(self):
        return {}

    @property
    def blocked(self):
        return {}


class BugzillaBug(Bug):
    def get_owner(self, data):
        return data['assigned_to']

    def get_reporter(self, data):
        return data['reporter']

    @property
    def id(self):
        return self.data['bug_id']

    @property
    def desc(self):
        return self.data['short_desc']

    @property
    def priority(self):
        return self.data['priority']

    @property
    def severity(self):
        return self.data['bug_severity']

    @property
    def status(self):
        return self.data['bug_status']

    @property
    def resolution(self):
        return self.data['resolution']

    @property
    def url(self):
        self.tracker.get_bug_url(self.id)

    @property
    def project_id(self):
        project_id = SelectorMapping(self.tracker).match(
            self.id,
            self.data['product'],
            self.data['component'],
            self.data['version'],
            )
        return project_id

    @property
    def opendate(self):
        return None

    @property
    def changeddate(self):
        return None

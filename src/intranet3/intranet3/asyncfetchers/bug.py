from intranet3.models import User
from intranet3.models.project import SelectorMapping
from intranet3.priorities import PRIORITIES


class ToDictMixin(object):

    def get_attrs(self):
        result = []
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            value = getattr(self, attr)
            if hasattr(value, '__call__'):
                continue
            result.append(attr)
        return result

    def to_dict(self):
        result = {}
        for attr in self.get_attrs():
            value = getattr(self, attr)
            if hasattr(value, 'to_dict'):
                value = value.to_dict()
            if isinstance(value, (list, tuple, set)):
                value = [
                    v.to_dict() if hasattr(v, 'to_dict') else v
                    for v in value
                ]
            result[attr] = value
        return result


class Scrum(ToDictMixin):
    def __init__(self):
        self.points = None
        self.velocity = 0.0
        self.color = None


class Bug(ToDictMixin):
    def __init__(self, tracker):
        self._tracker_type = tracker.type
        self._tracker_name = tracker.name

        self.id = ''
        self.time = 0.0
        self.desc = ''
        self.reporter = User(name='unknown', email='unknown')
        self.owner = User(name='unknown', email='unknown')
        self.priority = ''
        self.priority_number = 5  # 1 - 5
        self.severity = ''
        self.severity_number = 5  # 1 - 5
        self.status = ''
        self.resolution = ''
        self.project_name = ''
        self.component_name = ''
        self.version = ''
        self.project_id = None
        self.project = None
        self.deadline = ''
        self.opendate = None
        self.changeddate = None
        self.dependson = {}
        self.blocked = {}
        self.url = '#'
        self.labels = []

    def __repr__(self):
        return '<%s:%s:%s:%s>' % (
            self.__class__.__name__,
            self._tracker_type,
            self._tracker_name,
            self.id,
        )


class BaseScrumProducer(object):
    SCRUM_CLASS = Scrum

    def __init__(self, tracker, login_mapping, extra_data):
        self.tracker = tracker
        self.login_mapping = login_mapping
        self.extra_data = extra_data

    def __call__(self, bug, parsed_data):

        scrum = self.SCRUM_CLASS()
        data = (bug, self.tracker, self.login_mapping, parsed_data)

        attrs = self.get_attrs(*data)
        for attr in scrum.get_attrs():
            getter_name = 'get_%s' % attr
            if hasattr(self, getter_name):
                getter = getattr(self, getter_name)
                value = getter(*data)
            elif attr in attrs:
                value = attrs[attr]
            else:
                continue
            setattr(scrum, attr, value)
        return scrum

    def get_attrs(self, bug, tracker, login_mapping, parsed_data):
        return parsed_data


class BaseBugProducer(object):
    BUG_CLASS = Bug
    SCRUM_PRODUCER_CLASS = BaseScrumProducer

    def __init__(self, tracker, login_mapping, extra_data):
        self.tracker = tracker
        self.login_mapping = login_mapping
        self.extra_data = extra_data
        self.scrum_producer = self.SCRUM_PRODUCER_CLASS(
            tracker,
            login_mapping,
            extra_data,
        )

    def __call__(self, raw_data):
        parsed_data = self.parse(self.tracker, self.login_mapping, raw_data)

        data = (self.tracker, self.login_mapping, parsed_data)

        bug = self.BUG_CLASS(self.tracker)

        for attr in bug.get_attrs():
            # 2 ways of getting attribute value:
            # 1. from get_{attr} method if exists
            # 2. from parsed_data
            getter_name = 'get_%s' % attr
            if hasattr(self, getter_name):
                getter = getattr(self, getter_name)
                value = getter(*data)
            elif attr in parsed_data:
                value = parsed_data[attr]
            else:
                continue

            if attr in ('owner', 'reporter'):
                # we need user object for those:
                if value is not None:
                    value = self._resolve_user(value, self.login_mapping)
                else:
                    # no owner ! it means that bug.owner will be None !
                    value = None
            elif attr == 'id':
                value = str(value)

            setattr(bug, attr, value)

        bug.project_id = self.get_project_id_(self.tracker, bug)
        bug.scrum = self.scrum_producer(bug, parsed_data)
        return bug

    def _resolve_user(self, orig_login, login_mapping):
        return login_mapping.get(
            orig_login.lower(),
            User(name=orig_login, email=orig_login),
        )

    #
    # to override:
    #

    def get_priority_number(self, tracker, login_mapping, parsed_data):
        priority = 'unknown'

        if parsed_data.get('priority'):
            priority = parsed_data['priority']

        return PRIORITIES.get(priority.lower(), 5)

    def get_severity_number(self, tracker, login_mapping, parsed_data):
        severity = 'unknown'
        if parsed_data.get('severity'):
            severity = parsed_data['severity']
        return PRIORITIES.get(severity.lower(), 5)

    def parse(self, tracker, login_mapping, raw_data):
        """
        Parse raw_data initially,
        parsed data will be provided to each getter method like
        get_owner or get_attrs.
        Also it will be provided to Scrum constructor.
        """
        return raw_data

    def get_project_id_(self, tracker, bug):
        return SelectorMapping(tracker).match(
            bug.id,
            bug.project_name,
            bug.component_name,
            bug.version,
        )

    def get_attrs(self, tracker, login_mapping, parsed_data):
        """ Get the rest of attributes """
        return parsed_data

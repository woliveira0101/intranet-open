from intranet3.models import Base, User
from intranet3.models.project import SelectorMapping

class Scrum(object):
    ATTRIBUTES = {
        # possible attributes
        'points': 0,
        'velocity': 0,
    }

    def __init__(self, bug, tracker, login_mapping, parsed_data):

        data = (bug, tracker, login_mapping, parsed_data)

        attrs = self.get_attrs(*data)
        for attr, default_value in self.ATTRIBUTES:
            getter_name = 'get_%s' % attr
            if hasattr(self, getter_name):
                getter = getattr(self, getter_name)
                value = getter(*data)
            elif attr in attrs:
                value = attrs[attr]
            else:
                value = default_value
            setattr(self, attr, value)

    def get_attrs(self, bug, tracker, login_mapping, parsed_data):
        return parsed_data

    def to_dict(self):
        return {
            attr: getattr(self, attr)
            for attr in self.ATTRIBUTES.iterkeys()
        }


class Bug(object):
    Scrum = Scrum

    ATTRIBUTES = {
        # possible attributes
        'id': '',
        'time': 0.0,
        'desc': '',
        'reporter': User(name='unknown', email='unknown'),
        'owner': User(name='unknown', email='unknown'),
        'priority': '',
        'severity': '',
        'status': '',
        'resolution': '',
        'project_name': '',
        'component_name': '',
        'version': '',
        'project_id': None,
        'project': None,
        'deadline': '',
        'opendate': None,
        'changeddate': None,
        'dependson': {},
        'blocked': {},
        'labels': [],
        'url': '#',
    }

    def __init__(self, tracker, login_mapping, raw_data):
        # we shouldn't keep login_mapping inside Bug object
        # we do not need it to be pickled during memcached set

        parsed_data = self.parse(tracker, login_mapping, raw_data)

        data = (tracker, login_mapping, parsed_data)

        self.owner = self._resolve_user(
            self.get_owner(*data),
            login_mapping,
        )
        self.reporter = self._resolve_user(
            self.get_reporter(*data),
            login_mapping,
        )

        self.project_id = self.get_project_id(*data)

        attrs = self.get_attrs(*data)
        for attr, default_value in self.ATTRIBUTES:
            # 3 ways of getting attribute value:
            # 1. from get_{attr} method if exists
            # 2. from get_attrs returned data
            # 3. default value from ATTRIBUTES

            getter_name = 'get_%s' % attr
            if hasattr(self, getter_name):
                getter = getattr(self, getter_name)
                value = getter(*data)
            elif attr in attrs:
                value = attrs[attr]
            else:
                value = default_value

            if attr in ('owner', 'reporter'):
                # we need user object for those:
                value = self._resolve_user(value, login_mapping)

            setattr(self, attr, value)

        self.scrum = self.Scrum(self, *data)

    def _resolve_user(self, orig_login, login_mapping):
        return login_mapping.get(
            orig_login.lower(),
            User(name=orig_login, email=orig_login),
        )

    def to_dict(self):
        result = {}
        for attr in self.ATTRIBUTES.iterkeys():
            value = getattr(self, attr)
            if isinstance(value, (Scrum, Base)):
                value = value.to_dict()

            result[attr] = value

        return result
    #
    # to override:
    #

    def parse(self, tracker, login_mapping, raw_data):
        """
        Parse raw_data initially,
        parsed data will be provided to each getter method like
        get_owner or get_attrs.
        Also it will be provided to Scrum constructor.
        """
        return raw_data

    def get_project_id(self, tracker, login_mapping, parsed_data):
        return SelectorMapping(tracker).match(
            parsed_data['id'],
            parsed_data['product'],
            parsed_data['component'],
            parsed_data['version'],
        )

    def get_owner(self, tracker, login_mapping, parsed_data):
        """ Get tracker owner username """
        return None

    def get_reporter(self, tracker, login_mapping, parsed_data):
        """ Get tracker reporter username """
        return None

    def get_attrs(self, tracker, login_mapping, raw_data):
        """ Get the rest of attributes """
        return raw_data

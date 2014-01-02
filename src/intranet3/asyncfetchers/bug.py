# -*- coding: utf-8 -*-
from intranet3.log import EXCEPTION_LOG, INFO_LOG, DEBUG_LOG
from intranet3.lib.scrum import parse_whiteboard
from intranet3.priorities import PRIORITIES

EXCEPTION = EXCEPTION_LOG(__name__)
LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
_marker = object()

class Bug(object):

    def __init__(self,
                 tracker, id, desc, reporter, owner, priority, severity,
                 status, resolution, project_name, component_name, deadline,
                 opendate, changeddate,
                 dependson=_marker, blocked=_marker, whiteboard='', version='',
                 number=None, labels=None):
        self.time = 0.0
        self.tracker = tracker
        self.number = number  # Unique number for github
        self.id = str(id)
        self.desc = desc
        self.reporter = reporter
        self.owner = owner
        self.priority = priority
        self.severity = severity
        self.status = status
        self.resolution = resolution
        self.project_name = project_name
        self.component_name = component_name
        self.project = None
        self.deadline = deadline
        self.opendate = opendate
        self.changeddate = changeddate
        self.dependson = {} if dependson is _marker else dependson
        self.blocked = {} if blocked is _marker else blocked
        self.labels = labels

        if isinstance(whiteboard, basestring):
            self.whiteboard = parse_whiteboard(whiteboard)
        else:
            self.whiteboard = whiteboard
        self.version = version

    def get_url(self):
        raise NotImplementedError()

    def is_unassigned(self):
        raise NotImplementedError()

    @property
    def is_blocked(self):
        return False

    def get_status(self):
        """
        Convert tracker specific status to one of these:
        'NEW', 'ASSIGNED', 'REOPENED', 'UNCONFIRMED', 'CONFIRMED', 'WAITING', 'RESOLVED', 'VERIFIED'
        """
        raise NotImplementedError()

    @property
    def priority_number(self):
        priority = getattr(self, 'priority', 'unknown')
        return PRIORITIES.get(priority.lower(), 5)

    @property
    def severity_number(self):
        severity = getattr(self, 'severity', 'unknown')
        return PRIORITIES.get(severity.lower(), 5)

    def to_dict(self):
        response = {
            'id': self.id,
            'time': self.time,
            'desc': self.desc,
            'severity': self.severity,
            'severity_number': self.severity_number,
            'project_name': self.project_name,
            'component_name': self.component_name,
            'dependson': [(bug_id, value) for bug_id, value in self.dependson.iteritems()],
            'blocked': [(bug_id, value) for bug_id, value in self.blocked.iteritems()],
            'version': self.version,
            'priority': self.priority,
            'whiteboard': self.whiteboard,
            'url': self.get_url(),
            'owner_name': self.owner.name,
            'raporter_name': self.reporter.name,
            'opendate': self.opendate.strftime('%Y-%m-%d'),
            'changeddate': self.changeddate.strftime('%Y-%m-%d'),
            'deadline': self.deadline,
            'labels' : self.labels
        }

        if self.project:
            response.update({
                'project': {
                    'id': self.project.id,
                    'name': self.project.name,
                    'client_name': self.project.client.name
                }
            })
        else:
            response.update({
                'project': None,
                })

        return response

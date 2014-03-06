import copy

import pyflwor
from pyramid.decorator import reify


class Section(object):
    TMPL = """
for bug in <bugs>
where %s
return bug
"""

    def __init__(self, section, bugs):
        self.name = section['name']

        namespace = self._create_base_namespace()
        namespace['bugs'] = bugs

        condition = section['cond'].strip()

        if condition:
            query = self.TMPL % section['cond']

            try:
                self.bugs = pyflwor.execute(query, namespace)
            except Exception:
                self.bugs = []
        else:
            # no condition == all bugs
            self.bugs = bugs[:]

        #those bugs that was taken should be removed from global bug list
        for bug in self.bugs:
            bugs.remove(bug)

    @staticmethod
    def _create_base_namespace():
        """
            Creates base namespace for pyflwor compiler.
            It adds function like array that creates array.
        """

        namespace = {
            'True': True,
            'False': False,
            'array': lambda *args: list(args)
        }
        return namespace

    @reify
    def points(self):
        return sum(bug.scrum.points for bug in self.bugs if bug.scrum.points)


class Column(object):

    def __init__(self, column, bugs):

        self.name = column['name']

        self.sections = [
            Section(section, bugs)
            for section in reversed(column['sections'])
        ]

        self.sections = list(reversed(self.sections))

    @reify
    def points(self):
        return sum(section.points for section in self.sections)

    @reify
    def bugs(self):
        return [bug for section in self.sections for bug in section.bugs]


class Board(object):
    def __init__(self, sprint, bugs):

        # we have to copy bugs, because each section is removing their bugs
        # from the list

        self._resolve_blocked_and_dependson(bugs)
        self.bugs = bugs[:]
        bugs = bugs[:]

        self._sprint = sprint
        self._board_schema = sprint.get_board()

        self.columns = [
            Column(column, bugs)
            for column in reversed(self._board_schema)
        ]

        self.columns = list(reversed(self.columns))

    def _resolve_blocked_and_dependson(self, bugs):
        """
        Replace ids of blocked and dependson bug with real bugs from sprint
        """
        id_to_bug = {
            bug.id: bug
            for bug in bugs
        }

        def resolve_bug(blocked_or_dependson, id_to_bug):
            def copy_bug(bug):
                bug = copy.deepcopy(bug)
                bug.blocked = []
                bug.dependson = []
                return bug

            result = []
            for bod in blocked_or_dependson:
                if bod.id in id_to_bug:
                    result.append(copy_bug(id_to_bug[bod.id]))
            return result

        for bug in bugs:
            bug.blocked = resolve_bug(bug.blocked, id_to_bug)
            bug.dependson = resolve_bug(bug.dependson, id_to_bug)

    @reify
    def completed_column(self):
        return self.columns[-1]

    @reify
    def completed_bugs(self):
        return self.completed_column.bugs

    @reify
    def points(self):
        return sum(column.points for column in self.columns)

    @reify
    def points_achieved(self):
        return self.completed_column.points

    def to_dict(self):
        return [bug.to_dict() for bug in self.bugs]

    def is_completed(self, bug):
        return bug in self.completed_bugs

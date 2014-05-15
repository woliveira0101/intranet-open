from collections import namedtuple

from intranet3.asyncfetchers.bug import Bug, Scrum

from intranet3.lib.scrum import Board
from intranet3.testing import (
    IntranetWebTest,
    FactoryMixin,
)
from mock import MagicMock


class StickNoteColorTestCase(FactoryMixin, IntranetWebTest):
    def test_stick_note_color(self):

        color_status = {
            "OPEN": "#0000FF",
            "CLOSED": "#FF0000",
            "RANDOM": "#00FF00",
        }

        colors = [
            {"color": color, "cond": "bug.status == '{}'".format(status)}
            for status, color in color_status.iteritems()
        ]

        board_data = {
            "colors": colors,
            "board": [
                {
                    "sections": [
                        {"cond": "bug.status == 'OPEN'", "name": ""}
                    ],
                    "name": "OPEN"
                },
            ]
        }

        sprint = MagicMock()
        sprint.get_board.return_value = board_data

        Tracker = namedtuple('Tracker', 'type name')
        tracker = Tracker('type', 'name')

        bug_status = [
            'OPEN',
            'CLOSED1',
            'OPEN',
            'RANDOM2',
            'CLOSED',
            'RANDOM3',
            'OPEN',
        ]

        bugs = []

        for bug_status in bug_status:
            bug = Bug(tracker)
            bug.status = bug_status
            bug.scrum = Scrum()

            bugs.append(bug)

        Board(sprint, bugs)

        for bug in bugs:
            selected_color = color_status.get(bug.status)
            self.assertEqual(selected_color, bug.scrum.color)

# -*- coding: utf-8 -*-

import json
import colander
from pyramid.view import view_config
from pyramid.httpexceptions import (
    HTTPBadRequest, HTTPOk, HTTPNotFound, Response, HTTPForbidden
)
from sqlalchemy.exc import IntegrityError

from intranet3 import models as m
from intranet3 import helpers as h
from intranet3.utils.views import ApiView
from intranet3.schemas.sprint import BoardSchema
from intranet3.views.scrum.sprint import FetchBugsMixin
from intranet3.models import Sprint
from intranet3.lib.scrum import SprintWrapper
from intranet3.models import DBSession


@view_config(route_name='api_boards', renderer='json', permission="can_manage_sprint_boards")
class Boards(ApiView):

    def get(self):
        boards = [
            board.to_dict()
            for board in DBSession.query(m.SprintBoard)
        ]
        return dict(
            boards=boards
        )

    def post(self):
        json_board = self.request.json_body
        board_schema = BoardSchema()
        try:
            board = board_schema.deserialize(json_board)
        except colander.Invalid, e:
            errors = e.asdict()
            raise HTTPBadRequest(errors)

        board = m.SprintBoard(**board)
        board.user_id = self.request.user.id
        DBSession.add(board)

        try:
            DBSession.flush()
        except IntegrityError:
            raise HTTPBadRequest('Board exists')

        return dict(
            id=board.id,
        )


@view_config(route_name='api_board', renderer='json', permission="can_manage_sprint_boards")
class Board(ApiView):

    def put(self):
        board_id = self.request.matchdict.get('board_id')
        board = m.SprintBoard.query.get(board_id)
        if not board:
            raise HTTPNotFound()

        try:
            json_body = self.request.json_body
        except ValueError:
            raise HTTPBadRequest('Expect json')

        schema = BoardSchema()
        try:
            board = schema.deserialize(json_body)
        except colander.Invalid, e:
            errors = e.asdict()
            raise HTTPBadRequest(errors)

        for key, value in board.iteritem():
            setattr(board, key, value)

        return HTTPOk('OK')

    def delete(self):
        board_id = self.request.matchdict.get('board_id')
        board = m.SprintBoard.query.get(board_id)

        if not board:
            raise HTTPNotFound()

        can_delete = (board.user_id == self.request.user.id)

        if not can_delete:
            raise HTTPForbidden

        DBSession.delete(board)

        return HTTPOk('OK')

@view_config(route_name='api_sprint_bugs', renderer='json', permission="can_manage_sprint_boards")
class Bugs(FetchBugsMixin, ApiView):
    def get(self):
        sprint_id = self.request.matchdict.get('sprint_id')
        sprint = Sprint.query.get(sprint_id)
        bugs = self._fetch_bugs(sprint)

        sw = SprintWrapper(sprint, bugs, self.request)
        response = json.dumps([
            bug.to_dict()
            for bug in sw.board.bugs
        ], default=h.json_dumps_default, sort_keys=True)

        return Response(
            response,
            content_type='application/json',
        )

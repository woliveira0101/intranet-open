import datetime

from markupsafe import Markup

from pyramid.httpexceptions import HTTPForbidden
from pyramid.events import subscriber
from pyramid.events import BeforeRender, ContextFound


class PresenceTracking(object):
    def __init__(self, event):
        today = datetime.date.today()
        session = event['request'].db_session

        user = event['request'].user
        self.arrival = None
        if not user:
            return
        row = session.query('ts').from_statement("""
            SELECT MIN(p.ts) as "ts"
            FROM presence_entry p
            WHERE DATE(p.ts) = :today
              AND p.user_id = :user_id
            """).params(today=today, user_id=user.id).first()

        if not (row and row.ts):
            return

        arrival = row.ts
        now = datetime.datetime.now()
        since_morning_hours = float((now - arrival).seconds) / 3600
        self.present = since_morning_hours
        noted = 0.0
        row = session.query('time').from_statement("""
            SELECT COALESCE(SUM(t.time), 0.0) as "time"
            FROM time_entry t
            WHERE t.date = :today
              AND t.user_id = :user_id
              AND t.deleted = FALSE
            """).params(user_id=user.id, today=today).first()
        if row:
            noted = row.time
        self.noted = noted
        self.remaining = since_morning_hours - noted
        self.arrival = arrival


def get_flashed_messages(request):
    def get_flashed_messages(*args, **kwargs):
        return [ (a, b) for a, b in request.session.pop_flash() ]
    return get_flashed_messages


@subscriber(BeforeRender)
def add_global(event):
    request = event['request']
    event['presence_tracking'] = PresenceTracking(event)
    event['get_flashed_messages'] = get_flashed_messages(event['request'])
    event['csrf_field'] = Markup('<input type="hidden" name="csrf_token" value="%s">' % request.session.get_csrf_token())


@subscriber(ContextFound)
def csrf_validation(event):
    request = event.request
    if request.registry.settings['DEBUG'] == 'True':
        return
    if not request.is_xhr and request.method == "POST":
        csrf_token = request.POST.get('csrf_token')
        if csrf_token is None or csrf_token != request.session.get_csrf_token():
            raise HTTPForbidden('CSRF token is missing or invalid')

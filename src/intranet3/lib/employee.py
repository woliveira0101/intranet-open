from intranet3.models import Leave
from intranet3.models import DBSession


def user_leave(request, year, user=None):
    if not user:
        user = request.user

    leave = Leave.query.filter(Leave.user_id == user.id)\
                       .filter(Leave.year == year).first()
    leave = leave.number if leave else 0
    used = DBSession.query('days').from_statement("""
                SELECT sum(t.time)/8 as days
                FROM time_entry t
                WHERE deleted = false AND
                      t.project_id = 86 AND
                      date_part('year', t.date) = :year AND
                      t.user_id = :user_id
            """).params(year=year, user_id=user.id).first()
    if used and used[0]:
        used = int(used[0])
    else:
        used = 0
    left = leave - used
    return leave, used, left

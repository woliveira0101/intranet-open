from intranet3.models import TimeEntry, DBSession
from intranet3.log import DEBUG_LOG, WARN_LOG, EXCEPTION_LOG, INFO_LOG

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)
WARN = WARN_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)

def add_time(user_id, date, bug_id, project_id, hours, subject):
    # try finding existing entry for this bug
    bug_id = str(bug_id)
    entry = DBSession.query(TimeEntry).filter(TimeEntry.user_id==user_id) \
                         .filter(TimeEntry.date==date.date()) \
                         .filter(TimeEntry.ticket_id==bug_id) \
                         .filter(TimeEntry.project_id==project_id).first()
    if not entry:
        # create new entry
        entry = TimeEntry(
            user_id=user_id,
            date=date.date(),
            time=hours,
            description=subject,
            ticket_id=bug_id,
            project_id = project_id,
            modified_ts=date
        )
        LOG(u'Adding new entry')
    else:
        # update existing entry
        if not entry.frozen:
            entry.time += hours
            entry.modified_ts = date # TODO: this might remove an already existing lateness
            LOG(u'Updating existing entry')
            return entry
        else:
            LOG(u'Omission of an existing entry because it is frozen')

    return entry

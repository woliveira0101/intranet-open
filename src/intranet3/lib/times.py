import datetime
import copy

import xlwt
from jinja2 import escape
from pyramid.httpexceptions import HTTPForbidden, HTTPBadRequest
from pyramid.response import Response
from sqlalchemy.sql import or_, and_

from intranet3.utils.filters import comma_number
from intranet3.models import User, TimeEntry, Tracker, Project, Client
from intranet3.log import INFO_LOG, WARN_LOG, ERROR_LOG, DEBUG_LOG, EXCEPTION_LOG
from intranet3.helpers import previous_month
from intranet3.forms.times import TimeEntryForm

LOG = INFO_LOG(__name__)
WARN = WARN_LOG(__name__)
ERROR = ERROR_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


def user_can_modify_timeentry(user, date_):
    """
    Checks if user can modify timeentry, rule:
    User can modify timeentry for current month or
    previous month provided it is first day of month.
    """
    if 'admin' in user.groups:
        return True

    date = copy.copy(date_)

    if isinstance(date, datetime.datetime):
        date = date.date()

    today = datetime.date.today()

    diff = today - date

    if diff.days <= 0:
        # date in future or today
        return True

    if date.year == today.year and date.month == today.month:
        # the same month
        return True

    if today.day == 1:
        prev_today = previous_month(today)
        if date.year == prev_today.year and date.month == prev_today.month:
            # first of month, employee can change/add timeentry for previous month
            return True

    return False


class ProtectTimeEntriesMixin(object):

    def protect(self):
        if 'timeentry_id' in self.request.GET:
            # edit or delete
            timeentry_id = self.request.GET.get('timeentry_id')
            timeentry = TimeEntry.query.get(timeentry_id)
            date = timeentry.date
            if not user_can_modify_timeentry(self.request.user, date):
                raise HTTPForbidden()

            if not self.request.has_perm('admin'):
                if timeentry.deleted: # cannot edit an already deleted entry
                    return HTTPBadRequest()
                elif timeentry.user_id != self.request.user.id: # edit only own entries
                    return HTTPForbidden()
            self.v['timeentry'] = timeentry

        if 'date' in self.request.GET:
            # add
            date = self.request.GET.get('date')
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
            if not user_can_modify_timeentry(self.request.user, date):
                raise HTTPForbidden()
            self.v['date'] = date

        if 'user_id' in self.request.GET:
            if not self.request.has_perm('admin'):
                raise HTTPForbidden()
            self.v['user'] = User.query.get(self.request.GET.get('user_id'))


class TimesReportMixin(object):
    def _prepare_uber_query_for_sprint(self, sprint, bugs):
        query = self.session.query
        uber_query = query(Client, Project, TimeEntry.ticket_id, User, Tracker, TimeEntry.description, TimeEntry.date, TimeEntry.time)
        uber_query = uber_query.filter(TimeEntry.user_id==User.id) \
                               .filter(TimeEntry.project_id==Project.id) \
                               .filter(Project.tracker_id==Tracker.id) \
                               .filter(Project.client_id==Client.id)

        uber_query = uber_query.filter(TimeEntry.date>=sprint.start) \
                               .filter(TimeEntry.date<=sprint.end) \
                               .filter(TimeEntry.deleted==False)

        if bugs:
            or_list = []
            for bug in bugs:
                or_list.append(and_(TimeEntry.ticket_id==bug.id, TimeEntry.project_id==bug.project.id))

            uber_query = uber_query.filter(or_(*or_list))
        else:
            uber_query = uber_query.filter(TimeEntry.ticket_id.in_([]))


        uber_query = uber_query.order_by(Client.name, Project.name, TimeEntry.ticket_id, User.name)
        return uber_query


    def _prepare_uber_query(self, start_date, end_date, projects, users, ticket_choice):
        query = self.session.query
        uber_query = query(Client, Project, TimeEntry.ticket_id, User, Tracker, TimeEntry.description, TimeEntry.date, TimeEntry.time)
        uber_query = uber_query.filter(TimeEntry.user_id==User.id)\
                               .filter(TimeEntry.project_id==Project.id)\
                               .filter(Project.tracker_id==Tracker.id)\
                               .filter(Project.client_id==Client.id)

        if projects:
            uber_query = uber_query.filter(TimeEntry.project_id.in_(projects))

        uber_query = uber_query.filter(TimeEntry.date>=start_date)\
                               .filter(TimeEntry.date<=end_date)\
                               .filter(TimeEntry.deleted==False)

        if ticket_choice == 'without_bug_only':
            uber_query = uber_query.filter(TimeEntry.ticket_id=='')
        elif ticket_choice == 'meetings_only':
            meeting_ids = [t['value'] for t in TimeEntryForm.PREDEFINED_TICKET_IDS]
            uber_query = uber_query.filter(TimeEntry.ticket_id.in_(meeting_ids))

        if users and users != ([],):
            uber_query = uber_query.filter(User.id.in_(users))

        uber_query = uber_query.order_by(Client.name, Project.name, TimeEntry.ticket_id, User.name)
        return uber_query

    def _get_participation_of_workers(self, entries):
        participation_of_workers = {}
        participation_of_workers_sum = 0

        for client, project, bug_id, user, tracker, desc, date, time in entries:
            if user.name not in participation_of_workers:
                participation_of_workers[user.name] = time
            else:
                participation_of_workers[user.name] += time

            participation_of_workers_sum += time

        participation_of_workers = [(name, round(time, 2), round(100*time/participation_of_workers_sum, 2))
                                    for name, time in participation_of_workers.items()]
        participation_of_workers.sort(key=lambda k: k[1], reverse=True)
        return participation_of_workers


class Row(list):
    subrows = []
    row_counter = 0
    ##  Client, Project, TimeEntry.ticket_id, User
    ## possibilities:
    ## 1 1 1 1
    ## 0 0 0 0

    ## 1 0 0 0
    ## 1 1 0 0
    ## 1 1 1 0

    ## 0 0 0 1
    ## 1 0 0 1
    ## 1 1 0 1

    def __init__(self, row, subrows):
        self.subrows = subrows
        self._id = Row.row_counter
        Row.row_counter += 1
        super(Row, self).__init__(row)

    @property
    def id(self):
        return 'row%s' % self._id

    @property
    def klass(self):
        if len(self.subrows) > 0:
            return 'clickable'
        return ''

    @classmethod
    def _to_print(cls, entries):
        result = []
        for entry in entries:
            identifier = '%s_%s' % (entry[4].id, entry[2])
            ## for titles ajax fetching
            title = '<span class="ajax_changeable" data-id="%s">%s</span>' % (identifier, escape(entry[5]))

            row = [
                escape(entry[0].name),
                escape(entry[1].name),
                entry[2],
                escape(entry[3].name),
                title,
                entry[6].strftime('%d.%m.%Y'),
                comma_number(entry[7]),
                ]
            result.append(row)
        return result

    @classmethod
    def create_row(cls, entries, groupby):
        printful_entries = cls._to_print(entries)
        row = printful_entries[0][:]
        if len(entries) == 1:
            return cls(row, [])

        for i, gb in enumerate(groupby):
            if not gb:
                row[i] = '<b>Multiple entries</b>'
        if not groupby[2]:
            row[4] = '<b>Multiple entries</b>'
            row[5] = '<b>Multiple entries</b>'

        asum = sum([arow[7] for arow in entries])
        row[6] = '<b>%s</b>' % comma_number(asum)

        return cls(row, printful_entries)

    @classmethod
    def _isthesame(cls, row1, row2, groupby):
        if (not groupby[0] or row1[0] == row2[0]) and\
           (not groupby[1] or row1[1] == row2[1]) and\
           (not groupby[2] or row1[2] == row2[2]) and\
           (not groupby[3] or row1[3] == row2[3]):
            return True

        return False

    @classmethod
    def _group(cls, a_entries, groupby):
        entries = a_entries[:]

        while entries:
            subrow = [entries.pop()]
            poss = []

            for i, entry in enumerate(entries):
                if cls._isthesame(subrow[0], entry, groupby):
                    poss.append(i)

            for i in sorted(poss, reverse=True):
                subrow.append(entries.pop(i))
            yield subrow
            subrow = []

    @classmethod
    def from_ordered_data(cls, entries, groupby):
        rows = []
        for entry in cls._group(entries, groupby):
            row = cls.create_row(entry, groupby)
            rows.append(row)
        return rows


def dump_entries_to_excel(entries):
    def _format_row(a_row):
        row = list(a_row)
        row[0] = (row[0].name,)                                    #client
        row[1] = (row[1].name,)                                    #project
        row[2] = (row[2],)                                         #ticketid
        row[3] = (row[3].email,)                                   #email
        row[4] = (unicode(row[5]),)                                #desc
        date_xf = xlwt.easyxf(num_format_str='DD/MM/YYYY')
        row[5] = (row[6].strftime('%d/%m/%Y'), date_xf)            #date
        row[6] = (round(row[7], 2),)                               #time
        return row[:7]

    wbk = xlwt.Workbook()
    sheet = wbk.add_sheet('Hours')

    heading_xf = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center')
    headings = ('Client', 'Project', 'Ticket id', 'Employee', 'Description', 'Date', 'Time')
    headings_width = (x*256 for x in (20, 30, 10, 40, 100, 12, 10))
    for colx, value in enumerate(headings):
        sheet.write(0, colx, value, heading_xf)
    for i, width in enumerate(headings_width):
        sheet.col(i).width = width


    sheet.set_panes_frozen(True)
    sheet.set_horz_split_pos(1)
    sheet.set_remove_splits(True)

    for j, row in enumerate(entries):
        row = _format_row(row)
        for i, cell in enumerate(row):
            sheet.write(j+1, i, *cell)

    file_path = '/tmp/tmp.xls'
    wbk.save(file_path)

    file = open(file_path, 'rb')
    response = Response(
        content_type='application/vnd.ms-excel',
        app_iter = file,
        )
    response.headers['Cache-Control'] = 'no-cache'
    response.content_disposition = 'attachment; filename="report-%s.xls"' % datetime.datetime.now().strftime('%d-%m-%Y--%H-%M-%S')

    return file, response

import sys
import logging
import transaction
import random

from pyramid.paster import bootstrap
from sqlalchemy import engine_from_config
from pyramid.paster import get_appsettings, setup_logging



def script():
    argv = sys.argv[1:]
    if len(argv) < 2:
        print u'Path to config file must be given as a single parameter, for example "bin/script parts/etc/config.ini and then script name"'
        return
    config_file_path = argv[0]
    func = argv[1]
    if func not in globals():
        print u'There is no %s script function here' % func
        return

    if func in ('init_db',):
        globals()[func](config_file_path)
        return

    env = bootstrap(config_file_path)
    globals()[func](env)
    env['closer']()


def init_db(config_path):
    from intranet3.models import DBSession, Base
    setup_logging(config_path)
    settings = get_appsettings(config_path)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    print 'Done'

def make_admin(config_path):
    from intranet3.models import DBSession, Base
    from intranet3.models import User
    user_login = sys.argv[-1]
    if len(sys.argv) < 4:
        print u"Provide user login"
        return

    session = DBSession()

    user = session.query(User).filter(User.email==user_login).first()

    if not user:
        print u"No such user: %s" % user_login
        return

    if 'admin' in user.groups:
        print u'Removing %s from group admin' % user.name
        groups = list(user.groups)
        groups.remove('admin')
        user.groups = groups
    else:
        print u'Adding %s to group admin' % user.name
        groups = list(user.groups)
        groups.append('admin')
        user.groups = groups

    session.add(user)
    transaction.commit()


def migrate(config_path):
    from intranet3.models import DBSession, Sprint, SprintBoard
    import json

    def migrate_object(obj):
        board_json = obj.board

        if not board_json:
            return

        board = json.loads(board_json)

        if not isinstance(board, list):
            return

        board = {
            "board": board,
            "colors": [],
        }

        obj.board = json.dumps(board)

    for sprint_board in DBSession.query(SprintBoard):
        migrate_object(sprint_board)

    for sprint in DBSession.query(Sprint):
        migrate_object(sprint)

    transaction.commit()


def remove(config_path):
    from intranet3.models import *
    user_login = sys.argv[-1]
    session = DBSession()

    TrackerCredentials.query.delete()
    Sprint.query.delete()

    ac = ApplicationConfig.query.first()
    ac.office_ip = '127.0.0'
    ac.google_user_email = ''
    ac.google_user_password = 'asdasda'
    ac.freelancers = ''
    ac.hours_employee_project = ''
    ac.holidays_spreadsheet = ''
    session.add(ac)

    for i, client in enumerate(Client.query):
        print 'client %s' % i
        client.name = 'Client_%s' % i
        client.emails = ''
        client.google_card = ''
        client.google_wiki = ''
        client.selector = ''
        client.street = ''
        client.city = ' '
        client.postcode = ''
        client.nip = ''
        client.mailing_url = ''
        client.wiki_url = ''
        client.note = ''
        session.add(client)

    for i, project in enumerate(Project.query):
        print 'project %s' % i
        project.name = 'Project_%s' % i
        project.project_selector = ''
        project.component_selector = ''
        project.version_selector = ''
        project.ticket_id_selector = ''
        project.google_card = ''
        project.google_wiki = ''
        project.mailing_url = ''
        project.working_agreement = ''
        project.definition_of_done = ''
        project.definition_of_ready = ''
        project.continuous_integration_url = ''
        project.backlog_url = ''
        session.add(project)

    for i, user in enumerate(User.query):
        print 'user %s' % i
        user.email = 'user%s@stxnext.pl' % i
        user.name = 'User_%s' % i
        user.availability_link = ''
        user.tasks_link = ''
        user.skype = ''
        user.irc = ''
        user.phone = ''
        user.phone_on_desk = ''

        user.description = ''

        user.refresh_token = ''
        user._access_token = ''
        session.add(user)

    for i, timeentry in enumerate(TimeEntry.query):
        if i % 1000 == 0:
            print 'timeentry %s' % i
        timeentry.description = 'description %s' % i
        timeentry.ticket_id = i
        timeentry.time = round(random.uniform(0.1, 1.2), 2)
        session.add(timeentry)

    for i, tracker in enumerate(Tracker.query):
        print 'tracker %s' % i
        tracker.name = 'Tracker_%s' % i
        tracker.url = 'http://tracker%s.url.com' % i
        tracker.mailer = 'tracker_mailer_%s' % i
        session.add(tracker)

    transaction.commit()


def create_config(env):
    from intranet3.models import *
    import transaction
    config = ApplicationConfig(
        office_ip='',
        google_user_email='',
        google_user_password='',
        holidays_spreadsheet='',
        hours_employee_project='',
    )
    DBSession.add(config)
    transaction.commit()


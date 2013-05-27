import sys
import logging
import transaction

from pyramid.paster import bootstrap
from sqlalchemy import engine_from_config
from pyramid.paster import get_appsettings, setup_logging

from intranet3.models import DBSession, Base


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
    setup_logging(config_path)
    settings = get_appsettings(config_path)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    print 'Done'

def make_admin(config_path):
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


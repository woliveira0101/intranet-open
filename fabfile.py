from fabric.api import *

BRANCH = 'uwsgi'

NODE_PATH = '/opt/nodejs-0.10.26/bin/'

env.hosts = ['intranet_staging@tracs']


@task
def deploy():
    with cd('intranet'):
        with settings(warn_only=True):
            run('./bin/uwsgi --stop ./var/intranet-staging.pid')
        run('git pull origin {}'.format(BRANCH))
        run('python bootstrap.py')
        run('./bin/buildout -vNc devel.cfg')
        with cd('js'):
            run('{}npm install'.format(NODE_PATH))
            run('{}node ./node_modules/.bin/bower install'.format(NODE_PATH))
            run('{}node ./node_modules/.bin/grunt prod'.format(NODE_PATH))
        run('./bin/uwsgi ./parts/etc/uwsgi_production.ini')

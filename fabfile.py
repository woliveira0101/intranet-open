from fabric.api import *

GIT = 'https://github.com/tulustul/intranet.git'
BRANCH = 'staging_instance'

env.hosts = ['intranet_staging@tracs']
env.password = 'intrastx'


@task
def deploy():
    with cd('intranet'):
        run('git pull origin {}'.format(BRANCH))
        run('python bootstrap.py')
        run('./bin/buildout -vNc devel.cfg')
        with cd('js'):
            run('grunt prod')
        run('./bin/uwsgi uwsgi.ini')


@task
def create():
    run('git clone {} -b staging_instance'.format(GIT))

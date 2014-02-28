# Intranet

Application for managing a company.

## Features:

1. Time tracking.
2. Fetching times from trackers like bugzilla or tracs.
3. Generating time reports (for employees, clients, owners).
4. Managing employee's arrival/leave time.
5. Managing employee's absences/leaves.

## Installation guide

Development under Ubuntu

Created: May 2013

Updated: September 2013

Versions: Intranet 3.0.8; Ubuntu 13.04; PostgreSQL 9.1; Python 2.7.4

### Table of contents

1. Install and configure PostgreSQL, Memcached. [#](#1-install-and-configure-postgresql-memcached)
2. Fork and clone Intranet with git. [#](#2-fork-and-clone-intranet)
3. Install Intranet's system dependencies. [#](#3-install-intranets-system-dependencies)
4. Run Intranet's buildout. [#](#4-run-intranets-buildout)
5. Configure Intranet. [#](#5-configure-intranet)
6. Launch of. [#](#6-launch-of)



### 1. Install and configure PostgreSQL, Memcached
Intranet's development assumes that database server is on the same machine as the application.

#### PostgreSQL
Installation:
```bash
user~$ sudo apt-get install postgresql-9.1
```
After installation, database server is up. First step is to login as newly created user in ubuntu named `postgres` (it's PostgreSQL super user):
```bash
user~$ sudo su postgres
```
Now connect to PostgreSQL server. Create user with password. Then create database:
- connection is via non-TCP/IP.
- you can change user-name and you should change password.

```
postgres~$ psql
postgres=# CREATE ROLE intranet2 WITH LOGIN PASSWORD 'password';
postgres=# CREATE DATABASE intranetdb WITH OWNER intranet2;
```

To logout press `CTRL+D` twice.

Now test your newly created user and database:

```bash
user~$ psql -d intranetdb -h localhost -U intranet2 -W
Password for user intranet2: password
```

If you dumping already existing DB, please login as postgres and:
```bash
postgres~$ psql intranetdb < /tmp/intranet.sql
```

Remember to migrate DB into proper version. This SQLs can be found in `db_migrations`.


#### Memcached
```bash
user~$ sudo apt-get install memcached
```

### 2. Fork and clone Intranet

First fork [Intranet](https://github.com/stxnext/intranet) to your GitHub account. Then if you have [configured github's SSH keys](https://help.github.com/articles/generating-ssh-keys), you can simply do:

```bash
cd ~/
mkdir intranet
cd intranet
git init
git clone git@github.com:"user"/intranet.git
```
Intranet source code lie down on your hard drive with path `~/intranet/intranet`.

### 3. Install Intranet's system dependencies

Intranet is written under Python 2.7. On Ubuntu you should have 2.7 pre-installed. Type `python -V` to version checking.

First install python-dev:
```bash
user~$ sudo apt-get install python-dev
```
#### PIL dependencies
Install PIL JPEG and ZLIB system dependencies.
```bash
user~$ sudo apt-get install libjpeg62 libjpeg62-dev zlib1g-dev
```
Them symlink them according to your professor architecture
```bash
"32-bit"
user~$ sudo ln -s /usr/lib/i386-linux-gnu/libz.so /usr/lib/libz.so
user~$ sudo ln -s /usr/lib/i386-linux-gnu/libjpeg.so /usr/lib/libjpeg.so
"64-bit"
user~$ sudo ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib/libz.so
user~$ sudo ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib/libjpeg.so
```
In section 4[#](#4-run-intranets-buildout), after PIL installation table like this should occurs
```
--------------------------------------------------------------------
  PIL 1.1.7 SETUP SUMMARY
  --------------------------------------------------------------------
  version       1.1.7
  platform      darwin 2.7.2 (default, Oct 11 2012, 20:14:37)
                [GCC 4.2.1 Compatible Apple Clang 4.0 (tags/Apple/clang-418.0.60)]
  --------------------------------------------------------------------
  --- TKINTER support available
  --- JPEG support available
  --- ZLIB (PNG/ZIP) support available
  *** FREETYPE2 support not available
  *** LITTLECMS support not available
  --------------------------------------------------------------------
```

#### PyOpenSSL dependencies

Install OpenSSL development package. That way you get header files `.h`, their are required by pyOpenSSL installation.
```bash
sudo apt-get install libssl-dev
```

#### Psycopg2 dependencies

Install:
```bash
user~$ sudo apt-get install libpq-dev
```

#### Python-ldap dependencies

Install 2 packages. It also needs `libssl-dev`, but it is installed earlier.
```bash
user~$ sudo apt-get install libldap2-dev libsasl2-dev
```

#### Buildout dependencies
Build-essential is a package which contains stuff needed for building software (make, gcc, ...).
```bash
user~$ sudo apt-get install build-essential
```

### 4. Run Intranet's buildout
```bash
python bootstrap.py -d
```
- `-d` Use Distribute rather than Setuptools

```bash
./bin/buildout -vNc devel.cfg
```
- `-v` Lookup configuration file with specified distribution versions.
- `-N` Default mode always tries to get newest versions. Turn off with -N or buildout newest option set to false.
- `-c` After this option specify a configuration file.

### 5. Configure Intranet

Download configuration file name it [config.ini](#intranet-configuration-file) and put in `intranet\intranet`.

1. There are 7 lines with `/home/<user>` to edit with your username.
2. Modify line starts with `sqlalchemy.url =` with your data.
3. Replace <generate_this> in lines starts `CRON_SECRET_KEY` and `DATASTORE_SYMMETRIC_PASSWORD` with this command outputs
4. Replace `example.com` domain with your company domain.

```bash
user~$ head -c 64 /dev/urandom | base64 -w 0
```
### 6. Launch of

After making configuration file get into `~/intranet/intranet/`

- Initialize database
```bash
./bin/script config.ini init_db
```

- Compile `*.less` and minimize `*.js` files
```bash
cd js
npm install
bower install
grunt dev
```

- Run development server
```bash
./bin/uwsgi parts/etc/uwsgi_local.ini
```

I'll just leave this here [http://localhost:5000/](http://localhost:5000/)

##### Intranet configuration file

```ini
###
# app configuration
# http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/environment.html
###

[app:main]
use = egg:intranet3

# reloading is not working because we are using twisted !
pyramid.reload_templates = false
pyramid.debug_authorization = false
pyramid.debug_notfound = false
pyramid.debug_routematch = false
pyramid.default_locale_name = en
pyramid.includes =
    pyramid_debugtoolbar
    pyramid_tm
	pyramid_beaker
	pyramid_jinja2
	pyramid_exclog

pyramid.autoroute.root_module = intranet3.views
sqlalchemy.url = postgresql://<intranet2>:<password>@localhost:5432/<intranetdb>
sqlalchemy.pool_size = 20
sqlalchemy.pool_timeout = 60
sqlalchemy.pool_recycle = 3600
jinja2.extensions = jinja2.ext.with_
jinja2.directories = intranet3:templates
jinja2.filters =
	slugify = intranet3.utils.filters.slugify
	parse_user_email = intranet3.utils.filters.parse_user_email
	parse_datetime_to_miliseconds = intranet3.utils.filters.parse_datetime_to_miliseconds
	timedelta_to_minutes = intranet3.utils.filters.timedelta_to_minutes
	comma_number = intranet3.utils.filters.comma_number
	format_time = intranet3.utils.filters.format_time
venusian.ignore = intranet3.loader

session.type = file
session.url = 127.0.0.1:11211
session.lock_dir = /home/<user>/intranet/intranet/var/beaker/sessions/data
session.data_dir = /home/<user>/intranet/intranet/var/beaker/sessions/lock
session.secret = /AqcOMcps/3NEE7oEOayDn53A25iEFFl
session.cookie_on_exception = true
session.auto = True


DEBUG = True
CRON_DISABLE = True
CRON_URL = http://localhost:5000
CRON_SECRET_KEY = <generate_this>
MEMCACHE_URI = 127.0.0.1:11211
REPEATER_FILE = /home/<user>/intranet/intranet/var/repeater.pickle
FRONTEND_PREFIX = http://localhost:5000
DATASTORE_SYMMETRIC_PASSWORD = <generate_this>
AVATAR_PATH = /home/<user>/intranet/intranet/var/thumbs/
SESSION_KEY = s0ecret
# gogole credentials for localhost:5000 !
GOOGLE_CLIENT_ID = 317757513490-7jdrej7gk02l97va89vbfi10qbg78qet.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET = wVhyUuQjKH6xgYlM4RcTymaR
GOOGLE_DEVELOPERS_KEY = AIzaSyCuzRrhRTNYmppML9EIxbCVCKXWc6HhUXU
MANAGER_EMAIL = example@example.com
COMPANY_DOMAIN = example.com
COMPANY_MAILING_LIST = group@example.com
ACCOUNTANT_EMAIL = accountant@example.com
# ldap or google
AUTH_TYPE = google

# By default, the toolbar only appears for clients from IP addresses
# '127.0.0.1' and '::1'.
# debugtoolbar.hosts = 127.0.0.1 ::1

###
# wsgi server configuration
###

[server:main]
use = egg:waitress#main
host = 127.0.0.1
port = 5000

###
# logging configuration
# http://docs.pylonsproject.org/projects/pyramid/en/latest/narr/logging.html
###

[loggers]
keys = root, intranet3, twisted, sql

[handlers]
keys = console, mainfile, twistedfile, sqlfile, intranet3file

[formatters]
keys = generic

[formatter_generic]
format = %(asctime)s %(levelname)s [%(name)s] %(message)s

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = DEBUG
formatter = generic

[handler_twistedfile]
class = handlers.TimedRotatingFileHandler
args = (os.path.join(r'/home/<user>/intranet/intranet', 'var', 'log', 'twisted.log'), 'MIDNIGHT')
level = DEBUG
formatter = generic

[handler_intranet3file]
class = handlers.TimedRotatingFileHandler
args = (os.path.join(r'/home/<user>/intranet/intranet', 'var', 'log', 'intranet.log'), 'MIDNIGHT')
level = WARN
formatter = generic

[handler_sqlfile]
class = handlers.TimedRotatingFileHandler
args = (os.path.join(r'/home/<user>/intranet/intranet', 'var', 'log', 'sqlalchemy.log'), 'MIDNIGHT')
level = DEBUG
formatter = generic

[handler_mainfile]
class = handlers.TimedRotatingFileHandler
args = (os.path.join(r'/home/<user>/intranet/intranet', 'var', 'log', 'main.log'), 'MIDNIGHT')
level = DEBUG
formatter = generic

[logger_root]
level = WARN
handlers = console

[logger_twisted]
level = WARN
handlers = console
qualname = twisted
propagate = 0

[logger_sql]
level = WARN
handlers = console
qualname = sqlalchemy
propagate = 0

[logger_intranet3]
level = DEBUG
handlers = console
qualname = intranet3
propagate = 0
```

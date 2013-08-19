from setuptools import setup, find_packages
import os

name = "intranet3"
version = "0.8.12"


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

dependency_links = [
    'http://github.com/krotkiewicz/pyramid_autoroute/tarball/master#egg=pyramid_autoroute',
]

setup(
    name=name,
    version=version,
    description="New Intranet version",
    long_description=read('README.md'),
    # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[],
    keywords="",
    author="",
    author_email='',
    url='',
    license='',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    zip_safe=False,
    dependency_links=dependency_links,
    install_requires=[
        'setuptools',
        'pyramid',
        'SQLAlchemy',
        'transaction',
        'pyramid_tm',
        'pyramid_debugtoolbar',
        'pyramid_beaker',
        'pyramid_jinja2',
        'pyramid_autoroute',
        'pyramid_exclog',
        'zope.sqlalchemy',
        'waitress',
        'psycopg2',
        'WTForms',
        'gdata==2.0.17',
        'ordereddict==1.1',
        'python-memcached==1.47',
        'Twisted==11.0.0',
        'PyOpenSSL',
        'twisted.scheduling==1.0',
        'python-dateutil==1.5',
        'xlwt<=0.7.4',
        'pil==1.1.7',
        'requests<=0.14.2',
        'certifi',
        'paste',
        'pyramid_ldap',
        'google-api-python-client',
        'werkzeug', # good memcached wrapper
        'Babel',
        'nose',
        'webtest',
        'Mock',
        'markdown',

    ],
    message_extractors = { 'src/intranet3': [
        ('**.py', 'python', None ),
        ('templates/**.html', 'jinja2', {'extensions': 'jinja2.ext.with_'}),
    ]},
    test_suite='intranet3.tests',
    entry_points="""\
    [console_scripts]
    run = intranet3:run
    twistd = intranet3.scripts.twistd:run
    script = intranet3.scripts:script
    [paste.app_factory]
    main = intranet3:main
    """,
)

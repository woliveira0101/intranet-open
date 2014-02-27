from .bugzilla import BugzillaFetcher
from .rockzilla import RockzillaFetcher
from .pivotaltracker import PivotalTrackerFetcher
from .unfuddle import UnfuddleFetcher
from .github import GithubFetcher
from .trac import TracFetcher
from .fake import FakeFetcher
from .jira import JiraFetcher

from .base import (
    FetchException,
    FetcherTimeout,
    FetcherBaseException,
    FetcherBadDataError,
)

FETCHERS = {
    'bugzilla': BugzillaFetcher,
    'rockzilla': RockzillaFetcher,
    'pivotaltracker': PivotalTrackerFetcher,
    'unfuddle': UnfuddleFetcher,
    'github': GithubFetcher,
    'trac': TracFetcher,
    'harvest': FakeFetcher,
    'jira': JiraFetcher,
}


def get_fetcher(tracker, credentials, user, login_mapping):
    type = tracker.type
    fetcher_class = FETCHERS[type]
    return fetcher_class(tracker, credentials, user, login_mapping)

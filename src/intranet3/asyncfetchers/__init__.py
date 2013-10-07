from intranet3.asyncfetchers.bugzilla import BugzillaFetcher
from intranet3.asyncfetchers.trac import TracFetcher
from intranet3.asyncfetchers.cookietrac import CookieTracFetcher
from intranet3.asyncfetchers.igozilla import IgozillaFetcher
from intranet3.asyncfetchers.bitbucket import BitBucketFetcher
from intranet3.asyncfetchers.rockzilla import RockzillaFetcher
from intranet3.asyncfetchers.pivotaltracker import PivotalTrackerFetcher
from intranet3.asyncfetchers.fake import FakeFetcher
from intranet3.asyncfetchers.unfuddle import UnfuddleFetcher
from intranet3.asyncfetchers.github import GithubFetcher
from intranet3.asyncfetchers.jira import JiraFetcher

FETCHERS = {
    'bugzilla': BugzillaFetcher,
    'igozilla': IgozillaFetcher,
    'trac': TracFetcher,
    'cookie_trac': CookieTracFetcher,
    'bitbucket': BitBucketFetcher,
    'rockzilla': RockzillaFetcher,
    'pivotaltracker': PivotalTrackerFetcher,
    'harvest': FakeFetcher,
    'unfuddle': UnfuddleFetcher,
    'github': GithubFetcher,
    'jira': JiraFetcher,
}

def get_fetcher(tracker, credentials, login_mapping):
    type = tracker.type
    fetcher_class = FETCHERS[type]
    return fetcher_class(tracker, credentials, login_mapping)

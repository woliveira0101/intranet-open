from nbugzilla import BugzillaFetcher

from nbase import FetchException, FetcherTimeout, FetcherBaseException

FETCHERS = {
   'bugzilla': BugzillaFetcher
}

def get_fetcher(tracker, credentials, login_mapping):
    type = tracker.type
    fetcher_class = FETCHERS[type]
    return fetcher_class(tracker, credentials, login_mapping)

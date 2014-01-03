
class FakeFetcher(object):
    """
    Used i.e. in Harvest tracker when we need credentials but don't fetcher
    """

    def __init__(self, *args, **kwargs):
        pass

    def fetch_user_tickets(self, *args, **kwargs):
        pass

    def fetch_all_tickets(self, *args, **kwargs):
        pass

    def fetch_user_resolved_bugs(self, *args, **kwargs):
        pass

    def fetch_all_resolved_bugs(self, *args, **kwargs):
        pass

    def fetch_bugs_for_query(self, *args, **kwargs):
        pass

    def fetch_resolved_bugs_for_query(self, *args, **kwargs):
        pass

    def fetch_bug_titles_and_depends_on(self, *args, **kwargs):
        pass

    def fetch_dependons_for_ticket_ids(self, *args, **kwargs):
        pass

    def fetch_user_resolved_tickets(self, *args, **kwargs):
        pass

    def fetch_all_resolved_tickets(self, *args, **kwargs):
        pass

    def get_result(self):
        return []

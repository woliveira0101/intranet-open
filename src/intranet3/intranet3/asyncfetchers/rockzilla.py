# -*- coding: utf-8 -*-
from .igozilla import IgozillaFetcher

KEYINGREDIENT_TRACKER_ID = 10


class RockzillaFetcher(IgozillaFetcher):
    delimiter=','

    def __init__(self, *args, **kwargs):
        super(RockzillaFetcher, self).__init__(*args, **kwargs)
        if self.tracker.id == KEYINGREDIENT_TRACKER_ID:
            self.encoding = 'utf-8'

    def common_url_params(self):
        params = super(RockzillaFetcher, self).common_url_params()
        params['columnlist'] = ",".join(self.COLUMNS)
        return params

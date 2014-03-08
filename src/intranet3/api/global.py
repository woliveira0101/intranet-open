# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config

from intranet3.utils.views import ApiView

hour9 = datetime.time(hour=9)

@view_config(route_name='api_globals', renderer='json')
class GlobalsApi(ApiView):
    def get(self):
        return self.request.globals

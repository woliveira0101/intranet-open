# coding: utf-8
from pyramid.view import view_config
from intranet3.utils.views import ApiView


@view_config(route_name='api_blacklist', renderer='json')
class BlacklistApi(ApiView):
    def get(self):
        blacklist = self.request.user.notify_blacklist
        return blacklist

    def post(self):
        blacklist = self.request.json.get('blacklist')
        self.request.user.notify_blacklist = blacklist
        return dict()

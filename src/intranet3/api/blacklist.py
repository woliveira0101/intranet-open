# coding: utf-8
from pyramid.view import view_config
from intranet3.utils.views import ApiView
from intranet3 import memcache

@view_config(route_name='api_blacklist', renderer='json')
class BlacklistApi(ApiView):
    def get(self):
        blacklist = self.request.user.notify_blacklist
        return blacklist

    def post(self):
        blacklist = self.request.json.get('blacklist')
        absences = self.return_users('absences', blacklist)
        lates = self.return_users('lates', blacklist)
        self.request.user.notify_blacklist = blacklist
        return dict(
            blacklist=blacklist,
            absences=absences,
            lates=lates
        )

    def return_users(self, name_list, blacklist):
        list = self.request.json.get(name_list)
        return [i for i in list if (i['id'] not in blacklist)]
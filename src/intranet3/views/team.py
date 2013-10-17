from pyramid.view import view_config
from intranet3.utils.views import BaseView
from intranet3.log import INFO_LOG

LOG = INFO_LOG(__name__)

@view_config(route_name='team_view')
class View(BaseView):
    def get(self):
        return {}

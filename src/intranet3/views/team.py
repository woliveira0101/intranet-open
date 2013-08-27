from pyramid.view import view_config
from intranet3.utils.views import BaseView
from intranet3.log import INFO_LOG

LOG = INFO_LOG(__name__)

@view_config(route_name='team_view', permission='admin')
class View(BaseView):
    def get(self):
        template = self.get_raw_template('team/teams.html')
        return {
            'template': template,
        }

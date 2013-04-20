import wtforms as wtf
from wtforms import validators
from pyramid.i18n import TranslationStringFactory

from intranet3.models import DBSession, Tracker, Project, Client
from intranet3.models.project import STATUS
from .utils import EntityChoices, UserChoices

_ = TranslationStringFactory('intranet3')


class ProjectForm(wtf.Form):
    """ Project form """
    name = wtf.TextField(_(u"Project name"), validators=[validators.Required()])
    coordinator_id = wtf.SelectField(_(u"Coordinator"), validators=[], choices=UserChoices(empty=True))
    tracker_id = wtf.SelectField(_(u"Tracker"), validators=[validators.Required()], choices=EntityChoices(Tracker, lambda tracker: tracker.name))
    status = wtf.SelectField(_(u"Status"), validators=[validators.Required()], choices=STATUS)
    turn_off_selectors = wtf.BooleanField(_(u"Turn off selectors"), validators=[])
    project_selector = wtf.TextField(_(u"Project selector"), validators=[])
    component_selector = wtf.TextField(_(u"Component selector"), validators=[])
    version_selector = wtf.TextField(_(u"Version selector"), validators=[])
    ticket_id_selector = wtf.TextField(_(u"Ticket ID selector"), validators=[])
    active = wtf.BooleanField(_(u"Active"), validators=[])
    google_card = wtf.TextField(_(u"Link to project card in google docs"), validators=[])
    google_wiki = wtf.TextField(_(u"Link to project wiki in google sites"), validators=[])
    mailing_url = wtf.TextField(_(u"Link to mailing group"), validators=[])
    
    def validate_component_selector(self, field):
        if field.data and not self.project_selector.data:
            raise validators.ValidationError(_(u"Cannot define component without a project"))
        
    def validate_ticket_id_selector(self, field):
        if field.data and (self.project_selector.data or self.component_selector.data):
            raise validators.ValidationError(_(u"Ticket ID selector disables project and component selectors"))
        value = field.data
        if value:
            for v in value.split(','):
                try:
                    int(v)
                except ValueError:
                    raise validators.ValidationError(_(u"Ticket IDs must be a comma-separated list of numbers"))


class ImportProjectForm(ProjectForm):
    
    def is_submitted(self):
        """
        Checks if form has been submitted. The default case is if the HTTP 
        method is **PUT** or **POST**.
        """
        return False


class ProjectChoices(EntityChoices):
    
    def __init__(self, empty=False, empty_title=u'-- None --',
                 skip_inactive=False, client=None,
                 additional_filter=lambda query: query):
        super(ProjectChoices, self).__init__(
            entity_class=Project, title_getter=None,
            empty=empty, empty_title=empty_title
        )
        self.skip_inactive = skip_inactive
        self.client = client
        self.a_filter = additional_filter
    
    def __iter__(self):
        if self.empty:
            yield '', self.empty_title
        query = DBSession.query(Project.id, Client.name, Project.name)\
                .filter(Project.client_id==Client.id)
        if self.client:
            query = query.filter(Project.client_id==self.client.id)
        if self.skip_inactive:
            query = query.filter(Project.active==True)
        query = query.order_by(Client.name, Project.name)
        query = self.a_filter(query).distinct()
        for project_id, client_name, project_name in query:
            yield str(project_id), u'%s / %s' % (client_name, project_name)
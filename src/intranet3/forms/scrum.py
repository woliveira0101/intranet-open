import wtforms as wtf
from wtforms import validators
from wtforms.widgets.core import html_params, HTMLString, text_type, escape

from pyramid.i18n import TranslationStringFactory

from intranet3.models import DBSession, Project, Sprint, Team

from intranet3.forms.project import ScrumProjectChoices, ScrumBugsProjectChoices

_ = TranslationStringFactory('intranet3')


class SprintProjectsWidget(wtf.widgets.Select):
    @classmethod
    def render_option(cls, value, label, selected, **kwargs):
        value, tracker_id = value
        options = dict(kwargs, value=value)
        if selected:
            options['selected'] = True
        options['data-tracker_id'] = tracker_id
        return HTMLString('<option %s>%s</option>' % (html_params(**options), escape(text_type(label))))


class SprintProjectsField(wtf.SelectMultipleField):
    widget = SprintProjectsWidget(multiple=True)

    def iter_choices(self):
        for (value, tracker_id), label in self.choices:
            selected = self.data is not None and self.coerce(value) in self.data
            yield ((value, tracker_id), label, selected)

    def pre_validate(self, form):
        if self.data:
            values = list(c[0][0] for c in self.choices)
            for d in self.data:
                if d not in values:
                    raise ValueError(self.gettext("'%(value)s' is not a valid choice for this field") % dict(value=d))


class SprintListFilterForm(wtf.Form):
    project_id = wtf.SelectField(_(u'Project'), validators=[])
    limit = wtf.IntegerField(_(u'Limit'), default=10)
    active_only = wtf.BooleanField(_(u'Active only'), default=False)

    def __init__(self, *args, **kwargs):
        super(SprintListFilterForm, self).__init__(*args, **kwargs)
        client = kwargs.pop('client', None)
        self.project_id.choices = ScrumProjectChoices(
            empty=True, skip_inactive=True, client=client,
            additional_filter=lambda query: query.filter(Project.id == Sprint.project_id),
        )


class TeamChoices(object):

    def __iter__(self):
        teams = DBSession.query(Team.id, Team.name).order_by(Team.name)
        yield '', u'-- None --'
        for team in teams:
            yield str(team.id), team.name

class SprintForm(wtf.Form):
    name = wtf.TextField(_(u"Sprint name"), validators=[validators.Required()])
    bugs_project_ids = SprintProjectsField(_(u"Bugs projects"), choices=ScrumBugsProjectChoices(skip_inactive=True), validators=[validators.Required()])
    project_id = wtf.SelectField(_(u"Project"), choices=ScrumProjectChoices(skip_inactive=True), validators=[validators.Required()])
    team_id = wtf.SelectField(_(u"Team"), choices=TeamChoices())
    start  = wtf.DateField(_(u"Start date"), format='%d/%m/%Y', validators=[])
    end  = wtf.DateField(_(u"End date"), format='%d/%m/%Y', validators=[])
    goal = wtf.TextAreaField(_(u'Goal'), validators=[])
    retrospective_note = wtf.TextAreaField(_(u'Retrospective note'), validators=[])

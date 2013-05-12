import wtforms as wtf
from wtforms import validators
from pyramid.i18n import TranslationStringFactory
from intranet3.models import Project, Sprint

from intranet3.forms.project import ProjectChoices

_ = TranslationStringFactory('intranet3')


class SprintListFilterForm(wtf.Form):
    project_id = wtf.SelectField(_(u'Project'), validators=[])
    limit = wtf.IntegerField(_(u'Limit'), default=10)
    active_only = wtf.BooleanField(_(u'Active only'), default=False)

    def __init__(self, *args, **kwargs):
        super(SprintListFilterForm, self).__init__(*args, **kwargs)
        client = kwargs.pop('client', None)
        self.project_id.choices = ProjectChoices(
            empty=True, skip_inactive=True, client=client,
            additional_filter=lambda query: query.filter(Project.id == Sprint.project_id),
        )


class SprintForm(wtf.Form):
    name = wtf.TextField(_(u"Sprint name"), validators=[validators.Required()])
    project_id = wtf.SelectField(_(u"Projects"), choices=ProjectChoices(), validators=[validators.Required()])
    start  = wtf.DateField(_(u"Start date"), format='%d/%m/%Y', validators=[])
    end  = wtf.DateField(_(u"End date"), format='%d/%m/%Y', validators=[])
    goal = wtf.TextAreaField(_(u'Goal'), validators=[])
    retrospective_note = wtf.TextAreaField(_(u'Retrospective note'), validators=[])

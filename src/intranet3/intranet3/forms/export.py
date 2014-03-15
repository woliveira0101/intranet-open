import wtforms as wtf
from wtforms import validators
from .utils import EntityChoices
from intranet3.models import Project

class TimeExportForm(wtf.Form):
    start_date = wtf.DateField(u"Start date", format='%d.%m.%Y', validators=[validators.Required()])
    end_date = wtf.DateField(u"End date", format='%d.%m.%Y', validators=[validators.Required()])
    project = wtf.SelectField(u"Project", choices=EntityChoices(Project, lambda project: u'%s / %s' % (project.client.name, project.name), empty=True))

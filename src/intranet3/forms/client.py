# -*- coding: utf-8 -*-
import wtforms as wtf
from wtforms import ValidationError, validators
from sqlalchemy.sql.expression import exists
from pyramid.i18n import TranslationStringFactory

from .utils import UserChoices, ListValidator
from intranet3.models import DBSession, Tracker, Client

_ = TranslationStringFactory('intranet3')

class TrackerChoices(object):
    def __iter__(self):
        yield None, '.:: select ::.'
        query = DBSession.query(Tracker.id, Tracker.name).order_by(Tracker.name)
        for id, name in query:
            yield str(id), name

class ClientForm(wtf.Form):
    """ Client form """
    name = wtf.TextField(_(u"Client name"), validators=[wtf.validators.Required()])
    coordinator_id = wtf.SelectField(u"Coordinator", validators=[], choices=UserChoices(empty=True))
    google_card = wtf.TextField(_(u"Link to project card in google docs"), validators=[])
    google_wiki = wtf.TextField(_(u"Link to project wiki in google sites"), validators=[])
    selector    = wtf.TextField(_(u"Selector"), validators=[])
    wiki_url    = wtf.TextField(_(u"Link to client wiki"), validators=[])
    mailing_url = wtf.TextField(_(u"Link to mailinglist"), validators=[])
    street      = wtf.TextField(_(u"Street"), validators=[])
    city        = wtf.TextField(_(u"City"), validators=[])
    postcode    = wtf.TextField(_(u"Post Code"), validators=[])
    nip         = wtf.TextField(_(u"NIP"), validators=[])
    note        = wtf.TextAreaField(_(u"Note"), validators=[])
    color       = wtf.TextField(_(u"Color"), validators=[])
    emails      = wtf.TextAreaField(_(u"Clients"), validators=[ListValidator(validators=[validators.Email()])])


class ClientAddForm(ClientForm):
    def validate_name(self, field):
        name = field.data
        if DBSession.query(exists().where(Client.name==name)).scalar():
            raise ValidationError(_(u'Client already exists', mapping={'name': name}))


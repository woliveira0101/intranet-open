# -*- coding: utf-8 -*-
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from intranet3.utils.views import BaseView
from intranet3.models import Client
from intranet3.log import INFO_LOG, WARN_LOG
from intranet3.forms.client import ClientForm, ClientAddForm
from intranet3.forms.common import DeleteForm

LOG = INFO_LOG(__name__)
WARN = WARN_LOG(__name__)


@view_config(route_name='client_view', permission='coordinator')
class View(BaseView):
    """ View an existing client """
    def get(self):
        client_id = self.request.GET.get('client_id')
        client = Client.query.get(client_id)
        return dict(client=client)


@view_config(route_name='client_list', permission='admin')
class List(BaseView):
    def get(self):
        clients = Client.query.order_by(Client.name)
        return dict(clients=clients)


class Counter():
    index = 0
    def __unicode__(self):
        self.index+=1
        return str(self.index)


@view_config(route_name='client_map', permission='coordinator')
class Map(BaseView):
    """ Map clients/projects/selectors """
    def get(self):
        clients = Client.query.order_by(Client.name)
        tab = self.request.GET.get('tab', 'active_clients')
        return dict(clients=clients,
                    tab=tab,
                    counter=Counter()
                    )


@view_config(route_name='client_add', permission='admin')
class Add(BaseView):
    """ Add new client """
    def dispatch(self):
        form = ClientAddForm(self.request.POST)
        if self.request.method == 'POST' and form.validate():
            coordinator_id = int(form.coordinator_id.data) if form.coordinator_id.data.isdigit() else None
            client = Client(
                name=form.name.data,
                google_card=form.google_card.data,
                google_wiki=form.google_wiki.data,
                color=form.color.data,
                selector=form.selector.data,
                emails=form.emails.data,
                coordinator_id=coordinator_id,
                street=form.street.data,
                city=form.city.data,
                postcode=form.postcode.data,
                nip=form.nip.data,
                note=form.note.data,
                wiki_url=form.wiki_url.data,
                mailing_url=form.mailing_url.data
            )
            self.session.add(client)
            self.session.flush()
            self.flash(self._(u"New client added"))
            LOG(u"Client added")
            return HTTPFound(location=self.request.url_for("/client/view", client_id=client.id))
        return dict(form=form)


@view_config(route_name='client_delete', renderer='intranet3:templates/common/delete.html', permission='admin')
class Delete(BaseView):
    def dispatch(self):
        client_id = self.request.GET.get('client_id')
        client =  Client.query.get(client_id)
        form = DeleteForm(self.request.POST)
        back_url = self.request.url_for('/client/list')
        if self.request.method == 'POST' and form.validate():
            client.projects.delete()
            self.session.delete(client)
            return HTTPFound(location=back_url)
        return dict(
            type_name=u'client',
            title=client.name,
            url=self.request.url_for('/client/delete', client_id=client.id),
            back_url=back_url,
            form=form
        )


@view_config(route_name='client_edit', permission='admin')
class Edit(BaseView):
    """ Edit an existing client """
    def dispatch(self):
        client_id = self.request.GET.get('client_id')
        client = Client.query.get(client_id)
        form = ClientForm(self.request.POST, obj=client)
        if self.request.method == 'POST' and form.validate():
            coordinator_id = int(form.coordinator_id.data) if form.coordinator_id.data.isdigit() else None

            client.name = form.name.data
            client.google_card = form.google_card.data
            client.google_wiki = form.google_wiki.data
            client.color=form.color.data
            client.selector = form.selector.data
            client.emails = form.emails.data
            client.coordinator_id = coordinator_id
            client.street = form.street.data
            client.city = form.city.data
            client.postcode = form.postcode.data
            client.nip = form.nip.data
            client.note = form.note.data
            client.wiki_url = form.wiki_url.data
            client.mailing_url = form.mailing_url.data

            self.session.add(client)
            self.flash(self._(u"Client saved"))
            LOG(u"Client saved")
            return HTTPFound(location=self.request.url_for("/client/view", client_id=client.id))
        projects = client.projects
        return dict(client_id=client.id, form=form, projects=projects)

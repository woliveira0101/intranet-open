# -*- coding: utf-8 -*-
import colander
from pyramid.view import view_config, view_defaults
from pyramid.httpexceptions import HTTPBadRequest, HTTPCreated, HTTPOk, HTTPNotFound
from sqlalchemy.exc import IntegrityError

from intranet3.utils.views import ApiView
from intranet3.models import Team as Team_m, TeamMember, User, Sprint, Project, Client
from intranet3.schemas.team import TeamAddSchema, TeamUpdateSchema
from intranet3.utils.decorators import has_perm
from intranet3 import helpers as h
from intranet3.api.preview import Preview


@view_config(route_name='api_teams', renderer='json')
class Teams(ApiView):

    def get(self):
        teams = self.session.query(Team_m, TeamMember.user_id)\
                            .filter(TeamMember.team_id==Team_m.id)

        team_to_project = self.session.query(Team_m.id, Project, Client)\
                                      .filter(Sprint.team_id==Team_m.id)\
                                      .filter(Sprint.project_id==Project.id)\
                                      .filter(Project.client_id==Client.id)\
                                      .order_by(Sprint.end.desc())

        teams = h.groupby(
            teams,
            lambda x: x[0],
            lambda x: x[1]
        )
        team_to_project = h.groupby(
            team_to_project,
            lambda x: x[0],
            lambda x: x[1:]
        )
        result = []
        for team, members in teams.iteritems():
            team = team.to_dict()
            team['users'] = members
            projects = team_to_project.get(team['id'], [])[:2] # two most recent projects
            team['projects'] = [
                dict(
                    id=project.id,
                    name=project.name,
                    client=dict(
                        id=client.id,
                        name=client.name,
                    ),
                ) for project, client in projects
            ]
            result.append(team)

        return dict(
            teams=result
        )

    @has_perm('admin')
    def post(self):
        try:
            json_team = self.request.json_body
        except ValueError:
            raise HTTPBadRequest('Expect json')
         
        team_schema = TeamAddSchema()
        try:
            team_des = team_schema.deserialize(json_team)
        except colander.Invalid, e:
            errors = e.asdict()
            raise HTTPBadRequest(errors)
        
        team = Team_m(name=team_des['name'])
        self.session.add(team)
        try:
            self.session.flush()
        except IntegrityError:
            raise HTTPBadRequest('Team exists')
        
        if team_des.get('swap_with_preview'):
            preview = Preview(self.request)
            if not preview.swap_avatar(type='teams', id=team.id):
                raise HTTPBadRequest('No preview to swap')

        return team.to_dict()


@view_config(route_name='api_team', renderer='json')
class Team(ApiView):
    def get(self):
        team_id = self.request.matchdict.get('team_id')
        team = Team_m.query.get(team_id)
        if team:
            return team.to_dict()
        else:
            raise HTTPNotFound()
    
    @has_perm('admin')
    def put(self):
        team_id = self.request.matchdict.get('team_id')
        team = Team_m.query.get(team_id)
        if not team:
            raise HTTPNotFound()
        
        try:
            json_team = self.request.json_body
        except ValueError:
            raise HTTPBadRequest('Expect json')
        
        team_schema = TeamUpdateSchema()
        try:
            team_des = team_schema.deserialize(json_team)
        except colander.Invalid, e:
            errors = e.asdict()
            raise HTTPBadRequest(errors)
        
        team.name = team_des.get('name') or team.name

        if 'users' in team_des:
            new_users = team_des['users']
            old_users = self.session.query(TeamMember.user_id).filter(TeamMember.team_id==team.id).all() 
            users_delete = list(set(old_users) - set(new_users))
            users_add = list(set(new_users) - set(old_users))

            if users_delete:
                TeamMember.query.filter(TeamMember.team_id==team.id)\
                                .filter(TeamMember.user_id.in_(users_delete))\
                                .delete(synchronize_session=False)
            
            if users_add:
                self.session.add_all([TeamMember(user_id=u_id, team_id=team.id) for u_id in users_add])
                
        if team_des.get('swap_with_preview'):
            preview = Preview(self.request)
            if not preview.swap_avatar(type='teams', id=team.id):
                raise HTTPBadRequest('No preview to swap')
        
        return HTTPOk("OK")

    @has_perm('admin')
    def delete(self):
        team_id = self.request.matchdict.get('team_id')
        team = Team_m.query.get(team_id)
        if not team:
            raise HTTPNotFound()

        TeamMember.query.filter(TeamMember.team_id==team.id).delete(synchronize_session=False)
        self.session.delete(team)

        return HTTPOk('OK')

@view_config(route_name='api_users', renderer='json')
class Users(ApiView):
    def get(self):
        full = self.request.GET.get('full') == '1'
        inactive = self.request.GET.get('inactive') == '1'

        users = User.query.order_by(User.name)

        if not (self.request.has_perm('admin') and inactive):
            users = users.filter(User.is_active==True)

        if full:
            return dict(
                users=[u.to_dict(full=True) for u in users],
            )
        else:
            users = users.filter(User.is_not_client())\
                         .filter(User.freelancer==False)
            return dict(
                users=[u.to_dict() for u in users],
            )



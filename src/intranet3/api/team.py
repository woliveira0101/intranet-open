# -*- coding: utf-8 -*-
import colander
from pyramid.view import view_config, view_defaults
from pyramid.httpexceptions import HTTPBadRequest, HTTPCreated, HTTPOk, HTTPNotFound
from sqlalchemy.exc import IntegrityError

from intranet3.utils.views import ApiView
from intranet3.models import Team as Team_m, TeamMember, User
from intranet3.schemas.team import TeamAddSchema, TeamUpdateSchema


@view_defaults(route_name='api_teams', renderer='json')
class Teams(ApiView):
    @view_config(request_method='GET')
    def get(self):
        return [t.to_dict() for t in Team_m.query.all()]
    
    @view_config(request_method='POST', permission='admin')
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
        
        return HTTPCreated('OK')
        

@view_defaults(route_name='api_team', renderer='json')   
class Team(ApiView):
    @view_config(request_method='GET')
    def get(self):
        team_id = self.request.matchdict.get('team_id')
        team = Team_m.query.get(team_id)
        if team:
            return team.to_dict()
        else:
            raise HTTPNotFound()
    
    @view_config(request_method='PUT', permission='admin')
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
        
        if team.name != team_des.get('name'):
            team.name = team_des['name']
            try:
                self.session.flush()
            except IntegrityError:
                raise HTTPBadRequest('Team exists')
        
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
        
        return HTTPOk("OK")
        

@view_config(route_name='api_users', renderer='json')
class Users(ApiView):
    def get(self):
        users = User.query.filter(User.is_active==True)\
                          .filter(User.is_not_client())\
                          .filter(User.freelancer==False)\
                          .order_by(User.name)
                          
        return [{'id': u.id, 'name': u.name, 'img': u.avatar_url} for u in users];


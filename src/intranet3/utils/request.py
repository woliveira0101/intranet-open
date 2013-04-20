import urlparse

from pyramid import request
from pyramid.security import authenticated_userid, has_permission
from pyramid.decorator import reify

from intranet3.models import DBSession
from intranet3 import models


class Request(request.Request):
    def __init__(self, *args, **kwargs):
        self.db_session = DBSession()
        super(Request, self).__init__(*args, **kwargs)

    @reify
    def user(self):
        user_id = authenticated_userid(self)
        if user_id:
            return self.db_session.query(models.User).get(user_id)

    def has_perm(self, perm):
        return has_permission(perm, self.context, self)

    def is_user_in_group(self, group):
        return self.user and group in self.user.groups

    @property
    def here(self):
        """The same as request.url but strips scheme + netloc"""
        url_parts = list(urlparse.urlparse(self.url))
        url_parts = ['', ''] + url_parts[2:]
        result = urlparse.urlunparse(url_parts)
        return result

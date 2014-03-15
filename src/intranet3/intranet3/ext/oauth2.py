import datetime
import httplib2
import logging
import urllib
from oauth2client.client import (OAuth2WebServerFlow, FlowExchangeError,
                                 OAuth2Credentials, _parse_exchange_token_response,
                                 _extract_id_token)

logger = logging.getLogger(__name__)

class OAuth2WebServerFlow(OAuth2WebServerFlow):
    def step2_exchange(self, code, http=None):
        """
        Don't send scope in step2
        """

        if not (isinstance(code, str) or isinstance(code, unicode)):
            if 'code' not in code:
                if 'error' in code:
                    error_msg = code['error']
                else:
                    error_msg = 'No code was supplied in the query parameters.'
                raise FlowExchangeError(error_msg)
            else:
                code = code['code']

        body = urllib.urlencode({
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
            })
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            }

        if self.user_agent is not None:
            headers['user-agent'] = self.user_agent

        if http is None:
            http = httplib2.Http()

        resp, content = http.request(self.token_uri, method='POST', body=body,
            headers=headers)
        d = _parse_exchange_token_response(content)
        if resp.status == 200 and 'access_token' in d:
            access_token = d['access_token']
            refresh_token = d.get('refresh_token', None)
            token_expiry = None
            if 'expires_in' in d:
                token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
                    seconds=int(d['expires_in']))

            if 'id_token' in d:
                d['id_token'] = _extract_id_token(d['id_token'])

            logger.info('Successfully retrieved access token')
            return OAuth2Credentials(access_token, self.client_id,
                self.client_secret, refresh_token, token_expiry,
                self.token_uri, self.user_agent,
                id_token=d.get('id_token', None))
        else:
            logger.info('Failed to retrieve access token: %s' % content)
            if 'error' in d:
                # you never know what those providers got to say
                error_msg = unicode(d['error'])
            else:
                error_msg = 'Invalid response: %s.' % str(resp.status)
            raise FlowExchangeError(error_msg)


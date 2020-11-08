# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import json
import logging

import requests
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


_logger = logging.getLogger(__name__)

TIMEOUT = 20

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_AUTH_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'


class GoogleException(Exception):
    """ Exception the missing configuration
    """
    def __init__(self, msg, action_id=False):
        self.message = msg
        self.action_id = action_id


class GoogleAPI(models.AbstractModel):
    _name = 'google.api'
    _description = 'Google Service API'

    @api.model
    def _get_api_credentials(self, raise_if_not_set=False):
        client_id = self.env['ir.config_parameter'].sudo().get_param('google_client_id', default=False)
        client_secret = self.env['ir.config_parameter'].sudo().get_param('google_client_secret', default=False)
        if not (client_id and client_secret):
            if raise_if_not_set:
                raise self.env['res.config.settings'].get_config_warning(_("Error: this action is prohibited. You should set up the Google API credentials in %(menu:base_setup.menu_config)s."))
        return (client_id, client_secret)

    # ---------------------------------------------------------
    # OAuth 2.0 Flow
    # ---------------------------------------------------------

    @api.model
    def _auth_authorize_url(self, addon_name, additionnal_state=False, return_url=False):
        scopes = self._api_get_scopes(addon_name)
        return self._auth_get_authorize_uri(scopes, additionnal_state=additionnal_state, return_url=return_url)

    @api.model
    def _auth_get_authorize_uri(self, scopes, additionnal_state=False, return_url=False):
        """ This method return the url needed to allow this instance of Odoo to access to the scope
            of gmail specified as parameters
            Documentation: see https://developers.google.com/identity/protocols/OAuth2WebServer
            :param scopes: list of scope name, separated by spaces (string)
            :param additionnal_state: dict of additionnal values to use in the calllback uri
            :param return_url: the url to redirect the user once he logged into google service
        """
        # TODO If no scope is passed, we use service by default to get a default scope ?????

        # create the odoo state for callback
        state = {
            'dbname': self.env.cr.dbname,
            'scopes': scopes,
            'return_url': return_url,
        }
        if additionnal_state:
            state.update(additionnal_state)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        client_id = self._get_api_credentials(raise_if_not_set=True)[0]

        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': client_id,
            'state': json.dumps(state),
            'scope': scopes,
            'redirect_uri': '%s/google_account/authentication' % (base_url,),
            'include_granted_scopes': 'false',  # we keep one token per asked scope
            'access_type': 'offline',
            'prompt': 'select_account consent',
        })
        return "%s?%s" % (GOOGLE_AUTH_ENDPOINT, encoded_params)

    @api.model
    def _auth_exchange_code_for_tokens(self, authorize_code, scopes):
        response = self._auth_fetch_access_token(authorize_code)

        access_token = response['access_token']
        refresh_token = response['refresh_token']
        expires_in = response['expires_in']

        self.env.user._set_google_token(scopes, access_token, refresh_token, expires_in)

    @api.model
    def _auth_fetch_access_token(self, authorize_code):
        """ Call Google API to exchange authorization code against token, with POST request, to
            not be redirected.
            Returned response:
                {
                  "access_token":"1/fFAGRNJru1FTz70BzhT3Zg",
                  "expires_in":3920,
                  "token_type":"Bearer",
                  "refresh_token":"1/xEoDL4iW3cxlI7yDbSRFYNG01kVKM2C-259HOF2aQbI"
                }
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        client_id, client_secret = self._get_api_credentials(raise_if_not_set=True)

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': '%s/google_account/authentication' % (base_url,)
        }
        try:
            res = requests.request('post', GOOGLE_AUTH_TOKEN_ENDPOINT, data=data, headers=headers, timeout=TIMEOUT)
            res.raise_for_status()
            return res.json()
        except requests.HTTPError:
            raise GoogleException(_("Something went wrong during your token generation. Maybe your Authorization Code is invalid"))

    @api.model
    def _auth_refetch_token(self, refresh_token):
        """ Send the refresh_token to get a new access token
            Returned response:
                {
                  "access_token":"1/fFAGRNJru1FTz70BzhT3Zg",
                  "expires_in":3920,
                  "token_type":"Bearer"
                }
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='http://www.odoo.com?NoBaseUrl')
        client_id, client_secret = self._get_api_credentials(raise_if_not_set=True)

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
        }
        try:
            res = requests.request('post', GOOGLE_AUTH_TOKEN_ENDPOINT, data=data, headers=headers, timeout=TIMEOUT)
            res.raise_for_status()
            return res.json()
        except requests.HTTPError as error:
            raise GoogleException(_("Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired "))

    # ---------------------------------------------------------
    # Google API Tools (for all services)
    # ---------------------------------------------------------

    def _api_do_request(self, endpoint, access_token, method='POST', params={}, additional_headers={}, timeout=False):
        """ Execute the request to Google API. Return a tuple ('HTTP_CODE', 'HTTP_RESPONSE')
            :param endpoint : the url to contact
            :param access_token: the access token to put in the headers to contact the API. Must be the one for the concerned scopes.
            :param params : dict or already encoded parameters for the request to make
            :param headers : headers of request
            :param method : the method to use to make the request
        """
        # chaging the headers
        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-type': 'application/x-www-form-urlencoded' if method == 'POST' else 'application/json',
            'Accept': 'text/plain',
        }
        for key, value in additional_headers.items():
            if key not in headers:
                headers[key] = value

        _logger.info("Uri: %s - Type : %s - Params : %s - header: %s!" % (endpoint, method, params, headers))

        timeout = timeout or TIMEOUT
        try:
            if method.upper() in ('GET', 'DELETE'):
                res = requests.request(method.lower(), endpoint, params=params, headers=headers, timeout=timeout)
            elif method.upper() in ('POST', 'PATCH', 'PUT'):
                res = requests.request(method.lower(), endpoint, data=params, headers=headers, timeout=timeout)
            else:
                raise Exception(_('Method not supported [%s] not in [GET, POST, PUT, PATCH or DELETE]!') % (method))

            res.raise_for_status()  # keep only 200s and 300s codes
            status = res.status_code

            if 300 <= status < 400:  # redicrection codes
                response = False
            else:
                response = res.json()

        except requests.HTTPError as error:
            try:
                # Typical google error
                # {'error': {'code': 403, 'message': 'Request had insufficient authentication scopes.', 'status': 'PERMISSION_DENIED'}}
                resp_content = error.response.json()
            except:
                resp_content = {}

            if resp_content.get('error'):
                self._api_handle_http_error(error.response.status_code, resp_content['error'])
            raise error

        return (status, response)

    def _api_handle_http_error(self, status, error):
        """ requests.response instance of the 'failed' request. The HTTP status of the given error
            will be between 400 and 600.
        """
        error_title = error.get('status')
        message = error.get('message')

        _logger.error("Google API returns error: [%s] %s : %s", status, error_title, message)

        if status in (401, 403, 498):  # Unauthorized, Forbidden, Token expired/invalid
            raise AccessError(_("Google Error Access: [%s] %s : %s") % (status, error_title, message))
        raise self.env['res.config.settings'].get_config_warning(_("Something went wrong with your request to google: %s") % (message,))

    def _api_get_scopes(self, app_name):
        scopes_map = self._api_scopes_map()
        scope_list = scopes_map.get(app_name, [])
        return ' '.join(scope_list)

    def _api_scopes_map(self):
        """ this map must be populated by Odoo addons requiering google api access, in the following format
            {
                'app_name': ['scope1', 'scope2'],
                'google_calendar': ['https://www.googleapis.com/auth/calendar.events.readonly']
            }
            The list of scopes for the app must be ONLY the one needed to use the odoo application. Some scopes
            are listed at https://developers.google.com/identity/protocols/googlescopes
        """
        return {}

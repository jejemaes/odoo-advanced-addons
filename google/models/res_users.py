# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields, models, _
from odoo.exceptions import UserError


def sort_scopes(scopes):
    if scopes:
        scopes_list = scopes.split(' ')
        scopes_list.sort()
        scopes = ' '.join(scopes_list)
    return scopes


class User(models.Model):
    _inherit = 'res.users'

    google_token_ids = fields.One2many('google.token', 'user_id', "Google Tokens", groups='base.group_system')

    def _get_google_token(self, scopes=False):
        scopes = sort_scopes(scopes)
        domain = [('user_id', '=', self.id), ('scopes', '=', scopes)]
        tokens = self.env['google.token'].sudo().search(domain, limit=1)
        if tokens:
            return tokens[0]
        return False

    def _set_google_token(self, scopes, access_token, refresh_token, expires_in):
        scopes = sort_scopes(scopes)
        expiration_date = datetime.now() + timedelta(seconds=expires_in)

        token = self._get_google_token(scopes)
        if token:
            token.write({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expiration_date': expiration_date,
            })
        else:
            token = self.env['google.token'].sudo().create({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expiration_date': expiration_date,
                'scopes': scopes,
                'user_id': self.id
            })

    # ----------------------------------------------------
    # ----------------------------------------------------
    # ----------------------------------------------------

    def _google_get_valid_token(self, scopes):
        """ get a valid access token per user. this implies to refresh them if needed. If not token
            (expired or not) exists, this method return False.
            :param scopes: list of google scope, separated by space
            :returns a dict with key is the user_id and the vaule is the access_token (str) or False
        """
        scopes = sort_scopes(scopes)
        tokens = self.env['google.token'].sudo().search([('scopes', '=', scopes), ('user_id', 'in', self.ids)])
        token_user_map = {token.user_id.id: token for token in tokens}

        access_token_per_user = dict.fromkeys(self.ids, False)

        for user in self:
            token = token_user_map.get(user.id)
            if token:
                if token.token_status == 'expired_token':
                    access_token_per_user[user.id] = user._google_auth_refresh_token(scopes, token.refresh_token)
                else:
                    access_token_per_user[user.id] = token.access_token
        return access_token_per_user

    def _google_auth_refresh_token(self, scopes, refresh_token):
        if not refresh_token:
            raise UserError(_("There is no token for user %s with scope '%s'") % (self.env.user.name, scopes))

        response = self.env['google.api']._auth_refetch_token(refresh_token)
        self._google_refresh_token(refresh_token, response['access_token'], response['expires_in'])
        return response['access_token']

    def _google_refresh_token(self, refresh_token, access_token, expires_in):
        """ Refresh the access token for the given refresh_token and return the new access token saved. """
        expiration_date = datetime.now() + timedelta(seconds=expires_in)

        token = self.env['google.token'].sudo().search([('refresh_token', '=', refresh_token), ('user_id', '=', self.id)])
        token.write({
            'access_token': access_token,
            'expiration_date': expiration_date,
        })
        return token

    def _google_token_status(self, scopes):
        scopes = sort_scopes(scopes)
        self.env.cr.execute("""
            SELECT
                user_id AS user_id,
                CASE
                   WHEN T.expiration_date <= NOW()
                   THEN 'expired_token'
                   ELSE 'valid_token'
                END AS token_status
            FROM google_token T
            WHERE user_id IN %s
                AND scopes = %s
        """, (tuple(self.ids), scopes,))
        user_token_status_map = {item['user_id']: item['token_status'] for item in self.env.cr.dictfetchall()}

        result = dict.fromkeys(self.ids, 'no_token')
        for user in self:
            if user.id in user_token_status_map:
                result[user.id] = user_token_status_map[user.id]
        return result

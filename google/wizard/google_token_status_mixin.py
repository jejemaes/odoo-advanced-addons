# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models


class GoogleAuthToken(models.AbstractModel):
    _name = 'google.token.status.mixin'
    _description = "Google Token Status Mixin"

    @api.model
    def default_get(self, fields):
        result = super(GoogleAuthToken, self).default_get(fields)
        # raise if API credentials not set up
        self.env['google.api']._get_api_credentials(raise_if_not_set=True)
        return result

    user_id = fields.Many2one('res.users', 'User', required=True, default=lambda self: self.env.user)
    token_status = fields.Selection([
        ('no_token', 'No Token'),
        ('expired_token', 'Expired Token'),
        ('valid_token', 'Valid Token')
    ], compute='_compute_token_status')

    @api.depends('user_id')
    def _compute_token_status(self):
        scopes = self.env['google.api']._api_get_scopes('website_gallery')
        status_map = self.mapped('user_id')._google_token_status(scopes)
        for wizard in self:
            wizard.token_status = status_map[wizard.user_id.id]

    def action_authorize_google(self):
        return_url = self._get_return_url_for_auth()
        url = self.env['google.api']._auth_authorize_url('website_gallery', return_url=return_url, additionnal_state={'uid': self.user_id.id})
        return {
            'name': 'Authorize Google Photos API',
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def _get_return_url_for_auth(self):
        return False

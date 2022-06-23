# -*- coding: utf-8 -*-

from odoo import api, fields, models


class GoogleToken(models.Model):
    _name = 'google.token'
    _description = "Google OAuth Token"

    user_id = fields.Many2one('res.users', 'User', required=True, copy=False)
    access_token = fields.Char("Authentification Token", copy=False, groups='base.group_system')
    refresh_token = fields.Char("Refresh Token", copy=False, groups='base.group_system')
    scopes = fields.Char('Google Scopes', copy=False)  # not required !
    expiration_date = fields.Datetime('Token Validity', required=True, copy=False)
    token_status = fields.Selection([
        ('valid_token', "Valid"),
        ('expired_token', "Expired"),
    ], string="Token Status", compute='_compute_token_status', store=False)

    _sql_constraints = [
        ('unique_scope_per_user', 'UNIQUE(user_id, scopes)', 'A google token is unique per user per scopes.'),
    ]

    @api.depends('expiration_date')
    def _compute_token_status(self):
        for token in self:
            if token.expiration_date < fields.Datetime.now():
                token.token_status = 'expired_token'
            else:
                token.token_status = 'valid_token'

# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_google = fields.Boolean("Google API Integrations")
    google_client_id = fields.Char("Client_id", config_parameter='google_client_id', default='')
    google_client_secret = fields.Char("Client_key", config_parameter='google_client_secret', default='')
    server_uri = fields.Char('URI for tuto')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            server_uri="%s/google_account/authentication" % get_param('web.base.url', default="http://yourcompany.odoo.com"),
        )
        return res

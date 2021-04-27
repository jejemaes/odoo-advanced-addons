# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = 'event.event'

    @api.onchange('use_registration')
    def _onchange_use_registration(self):
        if not self.use_registration:
            self.menu_register_cta = False

    @api.depends('use_registration')
    def _compute_menu_register_cta(self):
        super(EventEvent, self)._compute_menu_register_cta()
        for event in self:
            if not event.use_registration:
                event.menu_register_cta = False

    def _get_website_menu_entries(self):
        result = super(EventEvent, self)._get_website_menu_entries()
        if not self.use_registration:
            result = result[:-1]
            result.append((_('Details'), '/event/%s/register' % slug(self), False, 100, False),)
        return result

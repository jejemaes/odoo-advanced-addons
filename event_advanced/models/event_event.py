# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventEvent(models.Model):
    _inherit = 'event.event'

    use_registration = fields.Boolean("Allow Registration", compute='_compute_use_registration', default=True, readonly=False, store=True, help="Check this to allow people to register to the event and activate the attendees management")

    @api.depends('event_type_id')
    def _compute_use_registration(self):
        for event in self:
            event.use_registration = event.event_type_id.use_registration

    def action_edit_editor(self):
        self.ensure_one()
        view_form_id = self.env.ref('event_advanced.event_event_view_form_badge').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Edit Badge'),
            'display_name': _('Edit Badge'),
            'view_mode': 'form',
            'views': [(view_form_id, 'form')],
            'res_model': self._name,
            'res_id': self.id,
            'context': self.env.context,
        }

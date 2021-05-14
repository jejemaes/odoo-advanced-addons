# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventEvent(models.Model):
    _inherit = 'event.event'

    def action_edit_editor(self):
        self.ensure_one()
        view_form_id = self.env.ref('event_badge_editor.event_event_view_form_badge').id
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

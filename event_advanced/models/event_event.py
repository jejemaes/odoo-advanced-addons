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

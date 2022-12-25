# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventEvent(models.Model):
    _inherit = 'event.event'

    use_qrcode = fields.Boolean("Use QRCode on Registration", compute='_compute_use_qrcode', default=False, readonly=False, store=True)
    use_registration = fields.Boolean("Allow Registration", compute='_compute_use_registration', default=True, readonly=False, store=True, help="Check this to allow people to register to the event and activate the attendees management")

    @api.depends('event_type_id')
    def _compute_use_qrcode(self):
        for event in self:
            event.use_qrcode = event.event_type_id.use_qrcode

    @api.depends('event_type_id')
    def _compute_use_registration(self):
        for event in self:
            event.use_registration = event.event_type_id.use_registration

    @api.onchange('use_registration')
    def _onchange_use_registration(self):
        if not self.use_registration:
            self.use_qrcode = False
            self.seats_limited = False
            self.auto_confirm = False

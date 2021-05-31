# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventType(models.Model):
    _inherit = 'event.type'

    use_qrcode = fields.Boolean("Use QRCode on Registration")
    use_registration = fields.Boolean("Registration", default=True, help="Check this to allow people to register to the event and activate the attendees management")

    @api.onchange('use_registration')
    def _onchange_use_registration(self):
        if not self.use_registration:
            self.use_ticket = False
            self.use_qrcode = False

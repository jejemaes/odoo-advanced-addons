# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventType(models.Model):
    _inherit = 'event.type'

    use_qrcode = fields.Boolean("Use QRCode", help="Badge will contain a QRCode to scan to mark the customer as attended.")
    use_registration = fields.Boolean("Allow Registration", default=True, help="Check this to allow people to register to the event and activate the attendees management")
    registration_multi_qty = fields.Boolean("Allow Quantity on Registration", help="Allow multiple attendee on one registration (instead of one registration per customer).")

    @api.onchange('use_registration')
    def _onchange_use_registration(self):
        if not self.use_registration:
            self.use_qrcode = False
            self.has_seats_limitation = False
            self.auto_confirm = False
            self.registration_multi_qty = False

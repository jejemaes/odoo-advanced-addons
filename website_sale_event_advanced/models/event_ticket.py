# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventTicketType(models.Model):
    # Note: changing this model also change 'event.event.ticket' as it inherits from 'event.type.ticket'
    _inherit = 'event.type.ticket'

    online_pre_order = fields.Boolean("Pre-order", default=False, help="Allow to expose ticket online, but will not be included in a sale order. Registration are created and marked as not paid.")

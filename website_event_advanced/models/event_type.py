# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventType(models.Model):
    _inherit = 'event.type'

    registration_phone_mandatory = fields.Boolean("Phone Mandatory on Registration")
    website_hide_event_location = fields.Boolean("Hide Event Location")

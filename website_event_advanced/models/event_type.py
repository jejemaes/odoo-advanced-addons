# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventType(models.Model):
    _inherit = 'event.type'

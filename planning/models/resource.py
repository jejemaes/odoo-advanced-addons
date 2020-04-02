# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ResourceTime(models.Model):
    _inherit = 'resource.calendar.leaves'

    time_type = fields.Selection(selection_add=[('planning', 'Planning')])

    @api.model
    def get_unavailable_domain(self):
        domain = super(ResourceTime, self).get_unavailable_domain()
        return expression.OR([domain, [('time_type', '=', 'rental')]])

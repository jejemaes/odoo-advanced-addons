# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class Resource(models.Model):
    _inherit = 'resource.resource'

    color = fields.Integer("Color", default=1)


class ResourceTime(models.Model):
    _inherit = 'resource.calendar.leaves'

    time_type = fields.Selection(selection_add=[('rental', 'Rental')])

    _sql_constraints = [
        ('resource_id_required', "CHECK((time_type='rental' AND resource_id IS NOT NULL) or (time_type != 'rental'))", 'A rental time entry requires a resource.'),
    ]

    @api.onchange('resource_id')
    def onchange_resource(self):
        if self.resource_id:
            self.calendar_id = self.resource_id.calendar_id

    @api.model
    def get_unavailable_domain(self):
        domain = super(ResourceTime, self).get_unavailable_domain()
        return expression.OR([domain, [('time_type', '=', 'rental')]])

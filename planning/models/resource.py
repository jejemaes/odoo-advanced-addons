# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class Resource(models.Model):
    _inherit = 'resource.resource'

    # color = fields.Integer("Color", default=1)
    # context_rental_available = fields.Boolean("Is Resource available", compute='_compute_context_rental_available')

    # @api.depends('name')  # wrong depends...
    # # TODO JEM: v13 depends_context()
    # def _compute_context_rental_available(self):
    #     date_from = self._context.get('rental_date_from')
    #     date_to = self._context.get('rental_date_to')
    #     resource_unavailability_map = {}

    #     if date_from and date_to:
    #         date_from = fields.Datetime.from_string(date_from)
    #         date_to = fields.Datetime.from_string(date_to)

    #         if date_from < date_to:
    #             resource_unavailability_map = self.is_available(date_from, date_to)
    #     print(resource_unavailability_map)
    #     for resource in self:
    #         is_available = False
    #         if resource.id in resource_unavailability_map:
    #             is_available = bool(resource_unavailability_map[resource.id])
    #         resource.is_available = is_available


class ResourceTime(models.Model):
    _inherit = 'resource.calendar.leaves'

    time_type = fields.Selection(selection_add=[('planning', 'Planning')])

    # _sql_constraints = [
    #     ('resource_id_required', "CHECK((time_type='rental' AND resource_id IS NOT NULL) or (time_type != 'rental'))", 'A rental time entry requires a resource.'),
    # ]

    # @api.onchange('resource_id')
    # def onchange_resource(self):
    #     if self.resource_id:
    #         self.calendar_id = self.resource_id.calendar_id

    # @api.model
    # def get_unavailable_domain(self):
    #     domain = super(ResourceTime, self).get_unavailable_domain()
    #     return expression.OR([domain, [('time_type', '=', 'rental')]])

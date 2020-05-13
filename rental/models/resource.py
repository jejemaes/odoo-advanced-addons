# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ResourceTime(models.Model):
    _inherit = 'resource.calendar.leaves'

    time_type = fields.Selection(selection_add=[('rental', 'Rental')])
    rental_confirmed = fields.Boolean(compute='_compute_rental_confirmed', search='_search_rental_confirmed')

    _sql_constraints = [
        ('resource_id_required', "CHECK((time_type='rental' AND resource_id IS NOT NULL) or (time_type != 'rental'))", 'A rental time entry requires a resource.'),
    ]

    def _compute_rental_confirmed(self):
        raw_data = self.env['rental.booking'].search_read([('resource_time_id', 'in', self.ids), ('state', 'in', ['reserved', 'picked_up', 'returned', 'done'])], ['id'])
        data = [item['id'] for item in raw_data]
        for resource_time in self:
            resource_time.rental_confirmed = bool(resource_time.id in data)

    @api.model
    def _search_rental_confirmed(self, operator, value):
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            value = not value

        query = """
            SELECT B.resource_time_id
            FROM %s B
            WHERE B.state in ('reserved', 'picked_up', 'returned', 'done')
        """ % (self.env['rental.booking']._table)
        operator = 'inselect' if value else 'not inselect'

        return [('id', operator, (query, ()))]

    @api.onchange('resource_id')
    def onchange_resource(self):
        if self.resource_id:
            self.calendar_id = self.resource_id.calendar_id

    @api.model
    def get_unavailable_domain(self):
        domain = super(ResourceTime, self).get_unavailable_domain()
        return expression.OR([domain, ['&', ('time_type', '=', 'rental'), ('rental_confirmed', '=', True)]])

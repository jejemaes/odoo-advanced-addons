# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ResourceTime(models.Model):
    _inherit = 'resource.calendar.leaves'

    time_type = fields.Selection(selection_add=[('rental', 'Rental')])
    rental_booking_id = fields.Many2one('rental.booking', "Rental Booking", readonly=True, ondelete="set null")

    _sql_constraints = [
        ('resource_id_required', "CHECK((time_type='rental' AND resource_id IS NOT NULL) or (time_type != 'rental'))", 'A rental time entry requires a resource.'),
        ('rental_booking_id_required', "CHECK((time_type='rental' AND rental_booking_id IS NOT NULL) or (time_type != 'rental'))", 'A rental time entry requires a rental booking.'),
    ]

    @api.onchange('resource_id')
    def onchange_resource(self):
        if self.resource_id:
            self.calendar_id = self.resource_id.calendar_id

    @api.model
    def get_unavailable_domain(self):
        domain = super(ResourceTime, self).get_unavailable_domain()
        return expression.OR([domain, [('time_type', '=', 'rental')]])

# -*- coding: utf-8 -*-

from odoo import api, fields, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    payment_status = fields.Selection(selection_add=[
        ('pre_order', 'Pre Ordered')
    ], tracking=True)

    @api.depends('event_ticket_id')
    def _compute_payment_status(self):
        super()._compute_payment_status()
        for registration in self:
            if not registration.sale_order_line_id:
                if registration.event_ticket_id.online_pre_order:
                    registration.payment_status = 'paid' if registration.is_paid else 'pre_order'

    def action_mark_as_paid(self):
        self._action_set_paid()

    def action_mark_as_unpaid(self):
        self.write({'is_paid': False})

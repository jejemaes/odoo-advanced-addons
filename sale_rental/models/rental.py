# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class RentalBooking(models.Model):
    _inherit = 'rental.booking'

    sale_line_id = fields.Many2one('sale.order.line', 'Sale Item', readonly=True)
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', related='sale_line_id.order_id', readonly=True, store=True)

    def unlink(self):
        if any(rental.sale_line_id for rental in self):
            raise UserError(_("You can not remove rental linked to sale item."))
        return super(RentalBooking, self).unlink()

    # ---------------------------------------------------
    # Actions
    # ---------------------------------------------------

    @api.multi
    def action_view_so(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_order_id.id,
            "context": {"create": False, "show_sale": True},
        }

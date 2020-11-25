# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class RentalBooking(models.Model):
    _inherit = 'rental.booking'

    sale_line_id = fields.Many2one('sale.order.line', 'Sale Item', readonly=True)
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', related='sale_line_id.order_id', readonly=True, store=True)
    resource_product_id = fields.Many2one('product.product', related='resource_id.product_id', readonly=True)

    # ---------------------------------------------------
    # Actions
    # ---------------------------------------------------

    def action_create_so(self):
        return False

    def action_view_so(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_order_id.id,
            "context": {"create": False, "show_sale": True},
        }

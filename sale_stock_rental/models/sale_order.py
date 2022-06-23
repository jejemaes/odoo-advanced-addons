# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_qty_delivered_method(self):
        """ Stock take consu behaviorn but we don't want rental SOL for consu to be computed by
            stock moves (as there is no stock moves generated on SO confirmation)
            See override of `_action_launch_stock_rule` below.
        """
        super(SaleOrderLine, self)._compute_qty_delivered_method()

        for line in self:
            if line.is_rental and line.product_id.can_be_rented and line.product_id.type == 'consu' and line.product_id.rental_tracking == 'no':
                line.qty_delivered_method = 'manual'

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """ Prevent stock moves generation for rental order lines. """
        other_lines = self.filtered(lambda sol: not sol.is_rental)
        super(SaleOrderLine, other_lines)._action_launch_stock_rule(previous_product_uom_qty)

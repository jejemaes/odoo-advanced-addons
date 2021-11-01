# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError


class DeliveryPriceRule(models.Model):
    _inherit = "delivery.price.rule"

    variable = fields.Selection(selection_add=[('distance', 'Distance'), ('distance_qty', 'Distance * Quantity')], ondelete={'distance': 'cascade', 'distance_qty': 'cascade'})
    variable_factor = fields.Selection(selection_add=[('distance', 'Distance'), ('distance_qty', 'Distance * Quantity')], ondelete={'distance': 'cascade', 'distance_qty': 'cascade'})


class DeliveryGrid(models.Model):
    _inherit = 'delivery.carrier'

    distance_calculation = fields.Boolean("Required to compute the distance", compute='_compute_distance_calculation', store=True)
    distance_uom = fields.Selection([('km', 'Kilometer'), ('miles', 'Miles')], string="UoM for distance", default='km', required=True, help="UoM for distance used in price rules.")

    @api.depends('price_rule_ids.variable_factor', 'price_rule_ids.variable')
    def _compute_distance_calculation(self):
        for carrier in self:
            carrier.distance_calculation = bool(carrier.price_rule_ids.filtered(lambda rule: rule.variable == 'distance' or rule.variable_factor == 'distance'))

    def base_on_rule_rate_shipment(self, order):
        if self.distance_calculation:
            order.ensure_delivery_distance()
            self = self.with_context(order=order.sudo())
        return super(DeliveryGrid, self).base_on_rule_rate_shipment(order)

    def _get_price_dict(self, total, weight, volume, quantity):
        """ Enrich the sale_Eval context with the distance the UoM of the carrier """
        result = super(DeliveryGrid, self)._get_price_dict(total, weight, volume, quantity)
        order = self._context.get('order')
        distance_km = order.delivery_distance_km if order else 0.0
        distance_factor = 1 if self.distance_uom == 'km' else 1.60934
        result['distance'] = distance_km * distance_factor
        result['distance_qty'] = result['distance'] * quantity
        return result

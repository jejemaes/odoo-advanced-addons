# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_distance_km = fields.Float("Delivery Distance", readonly=True, help="Distance between the delivery address and the warehouse or the company (in kilometers).")

    def write(self, values):
        if any(fname in values for fname in self._delivery_get_distance_recalculation_fields()):
            values['delivery_distance_km'] = None

        result = super(SaleOrder, self).write(values)
        return result

    def _delivery_get_distance_recalculation_fields(self):
        return ['partner_shipping_id', 'company_id']

    def ensure_delivery_distance(self):
        geo_provider = self.env['base.geo_provider'].get_provider()
        for sale_order in self:
            if not sale_order.company_id.partner_id or not sale_order.partner_shipping_id:
                raise UserError(_("Missing address to compute distance on sale order %s") % (sale_order.display_name,))
            if not sale_order.delivery_distance_km:
                distance_meter = geo_provider.calculate_route_distance(sale_order.company_id.partner_id, sale_order.partner_shipping_id)
                distance_km = distance_meter/ 1000.0 if distance_meter else 0.0
                sale_order.write({'delivery_distance_km': distance_km})

    def _create_delivery_line(self, carrier, price_unit):
        sale_line = super(SaleOrder, self)._create_delivery_line(carrier, price_unit)
        if carrier.distance_calculation:
            distance_str = self.env['ir.qweb.field.float'].value_to_html(self.delivery_distance_km, {'decimal_precision': 'Product Unit of Measure'})
            sale_line.name += _("\nDelivery distance (used in price computation) is %s km.") % (distance_str,)
        return sale_line

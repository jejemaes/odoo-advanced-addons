# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from odoo.osv import expression
from odoo.addons.sale_rental.models.product import get_timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_rental_addional_line_values(self, product, origin_sale_line):
        result = super(SaleOrder, self)._prepare_rental_addional_line_values(product, origin_sale_line)
        result['linked_line_id'] = origin_sale_line.id
        return result

# -*- coding: utf-8 -*-

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('type')
    def _onchange_type_rental(self):
        if self.type == 'product':
            self.can_be_rented = False
            self.rental_tracking = None
            self.rental_tenure_type = None
            self.rental_tenure_ids = [(5, 0)]
            self.rental_calendar_id = None
            self.rental_tz = None
            self.rental_padding_before = False
            self.rental_padding_after = False


class Product(models.Model):
    _inherit = 'product.product'

    @api.onchange('type')
    def _onchange_type_rental(self):
        self.product_tmpl_id._onchange_type_rental()

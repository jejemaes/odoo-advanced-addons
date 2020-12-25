# -*- coding: utf-8 -*-
import math

from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.resource_advanced.models.resource import timezone_datetime


class Product(models.Model):
    _inherit = 'product.product'

    resource_ids = fields.One2many('resource.resource', 'product_id', string='Resources', domain=[('resource_type', '=', 'material')])
    resource_count = fields.Integer("Resource Count", compute='_compute_resource_count')

    @api.depends('resource_ids')
    def _compute_resource_count(self):
        grouped_data = self.env['resource.resource'].sudo().read_group([('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        mapped_data = {db['product_id'][0]: db['product_id_count'] for db in grouped_data}
        for product in self:
            product.resource_count = mapped_data.get(product.id, 0)

    @api.onchange('can_be_rented')
    def _onchange_can_be_rented(self):
        self.product_tmpl_id._onchange_can_be_rented()

    @api.onchange('rental_tenure_type')
    def _onchange_rental_tenure_type(self):
        self.product_tmpl_id._onchange_rental_tenure_type()

    @api.onchange('rental_tracking')
    def _onchange_rental_trakcing(self):
        if not self.rental_tracking:
            self.resource_ids = None

    # ----------------------------------------------------------------------------
    # Rental Pricing Methods
    # ----------------------------------------------------------------------------

    def get_rental_price_and_details(self, start_dt, end_dt, pricelist, quantity=1, currency=False, uom_id=False, date_order=False):
        return self.product_tmpl_id.get_rental_price_and_details(start_dt, end_dt, pricelist, quantity=quantity, currency=currency, uom_id=uom_id, date_order=date_order)

    def _get_rental_paddings_timedelta(self):
        before_padding = divmod(self.rental_padding_before * 60, 60)
        after_padding = divmod(self.rental_padding_after * 60, 60)
        return {
            'before': relativedelta(hours=before_padding[0], minutes=before_padding[1]),
            'after': relativedelta(hours=after_padding[0], minutes=after_padding[1]),
        }

    def get_product_multiline_description_sale(self):
        name = super(Product, self).get_product_multiline_description_sale()
        if self.can_be_rented and not self.sale_ok:
            name = self.display_name
        if self.description_rental:
            name += '\n' + self.description_rental
        return name

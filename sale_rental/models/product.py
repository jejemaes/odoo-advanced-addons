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

    rent_price_unit = fields.Float("Rental Unit Price", compute='_compute_rent_price_details', digits='Product Price')
    rent_price_explanation = fields.Char("Rental Unit Price Explanation", compute='_compute_rent_price_details')

    @api.depends('resource_ids')
    def _compute_resource_count(self):
        grouped_data = self.env['resource.resource'].sudo().read_group([('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        mapped_data = {db['product_id'][0]: db['product_id_count'] for db in grouped_data}
        for product in self:
            product.resource_count = mapped_data.get(product.id, 0)

    @api.depends('rental_tenure_ids.base_price')
    @api.depends_context('rental_start_dt', 'rental_end_dt', 'currency_id')
    def _compute_rent_price_details(self):
        """ Set the rental price unit for the context period, in the given currency (or the product one, if not given in context). """
        start_dt = self._context['rental_start_dt']
        end_dt = self._context['rental_end_dt']
        currency = self.env['res.currency'].browse(self._context['currency_id'])

        price_map = self.mapped('product_tmpl_id')._get_rental_price_unit(start_dt, end_dt, currency)
        for product in self:
            currency = currency or product.currency_id
            combinaison = price_map[product.product_tmpl_id.id]['combinaison']
            product.rent_price_unit = price_map[product.product_tmpl_id.id]['price_unit']
            product.rent_price_explanation = product.product_tmpl_id._rental_get_human_pricing_details(combinaison, show_price=True, currency_dst=currency)

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

    @api.onchange('type')
    def _onchange_service_for_rental(self):
        self.product_tmpl_id._onchange_service_for_rental()

    @api.onchange('rental_tenure_type')
    def _onchange_rental_tenure_type(self):
        self.product_tmpl_id._onchange_rental_tenure_type()

    @api.onchange('rental_tracking')
    def _onchange_rental_tracking(self):
        self.product_tmpl_id._onchange_rental_tracking()

    # ----------------------------------------------------------------------------
    # Rental Pricing Methods
    # ----------------------------------------------------------------------------

    def get_rental_price(self, start_dt, end_dt, pricelist_id, quantity=1.0, uom_id=False, date=False):
        pricelist = self.env['product.pricelist'].browse(pricelist_id)
        list_prices = pricelist.get_rental_list_price(self, start_dt, end_dt, date=date, quantity=quantity)

        result = {}
        for product in self.with_context(rental_start_dt=start_dt, rental_end_dt=end_dt, currency_id=pricelist.currency_id.id):
            list_price = list_prices[product.id]
            price_list, discount = pricelist.get_pricelist_discount(product.rent_price_unit, list_price, product=product, date=date)
            result[product.id] = {
                'price_list': price_list,
                'discount': discount,
            }
        return result

    def get_rental_pricing_explanation(self, start_dt, end_dt, currency_id=False, show_price=True):
        currency = None
        if currency_id:
            currency = self.env['res.currency'].browse(currency_id)

        price_map = self.mapped('product_tmpl_id')._get_rental_price_unit(start_dt, end_dt, currency)

        result = {}
        for product in self:
            #currency = self.env['res.currency'].browse(currency_id) if currency_id else product.currency_id
            current_currency = currency
            if not current_currency:
                current_currency = product.currency_id
            combinaison = price_map[product.product_tmpl_id.id]['combinaison']
            result[product.id] = product.product_tmpl_id._rental_get_human_pricing_details(combinaison, show_price=show_price, currency_dst=current_currency)
        return result

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

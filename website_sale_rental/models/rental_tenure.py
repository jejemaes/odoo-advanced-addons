# -*- coding: utf-8 -*-
import functools
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import add, subtract, start_of, end_of
from odoo import tools


class ProductRentalTenure(models.Model):
    _inherit = 'product.rental.tenure'

    website_base_price = fields.Float("Display price without pricelist applied", compute='_compute_website_base_price')
    website_list_price = fields.Float("Display price with pricelist applied", compute='_compute_website_list_price')

    @api.depends('base_price')
    @api.depends_context('website_id', 'uid')
    def _compute_website_base_price(self):
        website = self.env['website'].browse(self._context['website_id'])
        pricelist = website.get_current_pricelist()
        partner = self.env.user.partner_id

        tax_field = 'total_excluded' if self.user_has_groups('account.group_show_line_subtotals_tax_excluded') else 'total_included'

        result = {}
        price_data_map = self._get_tenure_grouped_by_template()
        for product_template, tenures in price_data_map.items():
            fpos = self.env['account.fiscal.position'].get_fiscal_position(partner.id).sudo()
            taxes = fpos.map_tax(product_template.sudo().taxes_id.filtered(lambda x: x.company_id == website.company_id), product_template, partner)

            for tenure in tenures:
                base_price = product_template.currency_id._convert(tenure.base_price, pricelist.currency_id, company=website.company_id, date=fields.Date.today())
                result[tenure.id] = taxes.compute_all(base_price, pricelist.currency_id, 1, product_template.product_variant_id, partner)[tax_field]

        for tenure in self:
            tenure.website_base_price = result.get(tenure.id, tenure.base_price)

    @api.depends('base_price')
    @api.depends_context('website_id', 'uid')
    def _compute_website_list_price(self):
        website = self.env['website'].browse(self._context['website_id'])
        pricelist = website.get_current_pricelist()
        partner = self.env.user.partner_id

        tax_field = 'total_excluded' if self.user_has_groups('account.group_show_line_subtotals_tax_excluded') else 'total_included'

        # apply website pricelist to tenures base price
        price_list_tenure_map = {}
        price_data_map = self._get_tenure_grouped_by_template()
        for product_template, tenures in price_data_map.items():

            sorted_tenures = tenures.sorted(key=lambda r: r.id)
            price_list = [product_template.currency_id._convert(t.base_price, pricelist.currency_id, company=website.company_id, date=fields.Date.today()) for t in sorted_tenures]

            converted_price_data_list = pricelist.apply_rental_pricelist_on_template(product_template, price_list, quantity=1.0)

            for tenure, list_price in zip(sorted_tenures, converted_price_data_list):
                price, discount = pricelist.get_pricelist_discount(tenure.base_price, list_price, product=product_template.product_variant_id, date=False)
                if discount:
                    price_list_tenure_map[tenure.id] = list_price  # base price with discount applied
                else:
                    price_list_tenure_map[tenure.id] = price  # base price without discount applied

        # apply company taxes of the product
        result = {}
        for product_template, tenures in price_data_map.items():
            fpos = self.env['account.fiscal.position'].get_fiscal_position(partner.id).sudo()
            taxes = fpos.map_tax(product_template.sudo().taxes_id.filtered(lambda x: x.company_id == website.company_id), product_template, partner)

            for tenure in tenures:
                list_price = price_list_tenure_map.get(tenure.id, 0)
                result[tenure.id] = taxes.compute_all(list_price, pricelist.currency_id, 1, product_template.product_variant_id, partner)[tax_field]

        for tenure in self:
            tenure.website_list_price = result.get(tenure.id, tenure.base_price)

    def _get_tenure_grouped_by_template(self):
        tenure_product_map = dict.fromkeys(self.mapped('product_template_id'), self.env['product.rental.tenure'])
        for tenure in self:
            tenure_product_map[tenure.product_template_id] |= tenure
        return tenure_product_map

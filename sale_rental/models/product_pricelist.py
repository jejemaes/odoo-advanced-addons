# -*- coding: utf-8 -*-

from itertools import chain

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr
from odoo.tools.misc import get_lang

from odoo.osv import expression


class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    # ----------------------------------------------------------------------------
    # Overrides
    # ----------------------------------------------------------------------------

    def _get_applicable_rules_domain(self, products, date, **kwargs):
        domain = super(Pricelist, self)._get_applicable_rules_domain(products, date, **kwargs)

        if kwargs.get('sale_is_rental'):
            subdomain = [('applicable_on', '=', 'rent')]
        else:
            subdomain = [('applicable_on', '=', 'sale')]
        return expression.AND([domain, subdomain])


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    applicable_on = fields.Selection([
        ('sale', 'Selling'),
        ('rent', 'Renting'),
    ], string="Mode", default='sale', required=True)

    @api.onchange('compute_price', 'applicable_on')
    def _onchange_compute_price_on_rental(self):
        if self.applicable_on == 'rent':
            self.base = 'list_price'

    @api.depends('applicable_on')
    def _compute_rule_tip(self):
        rent_rules = self.filtered(lambda rule: rule.applicable_on == 'rent')
        sale_rules = self.filtered(lambda rule: rule.applicable_on != 'rent')

        rent_rules.rule_tip = False
        for item in rent_rules:
            if item.compute_price != 'formula':
                continue
            base_amount = 100
            discount_factor = (100 - item.price_discount) / 100
            discounted_price = base_amount * discount_factor
            if item.price_round:
                discounted_price = tools.float_round(discounted_price, precision_rounding=item.price_round)
            surcharge = tools.format_amount(item.env, item.price_surcharge, item.currency_id)
            item.rule_tip = _(
                "Rent Price with a %(discount)s %% discount and %(surcharge)s extra fee\n"
                "Example: %(amount)s * %(discount_charge)s + %(price_surcharge)s → %(total_amount)s",
                discount=item.price_discount,
                surcharge=surcharge,
                amount=tools.format_amount(item.env, 100, item.currency_id),
                discount_charge=discount_factor,
                price_surcharge=surcharge,
                total_amount=tools.format_amount(
                    item.env, discounted_price + item.price_surcharge, item.currency_id),
            )

        super(PricelistItem, sale_rules)._compute_rule_tip()

    def _compute_base_price(self, product, quantity, uom, date, target_currency):
        # when no match pricelist rule is found on a SO, price computation still arrives here. So, we have to
        # check the product context to avoid having the sale prices as unit price (instead of the rental price).
        if self.applicable_on == 'rent' or (not self and product._context.get('sale_is_rental')):
            rental_start_date = product._context.get('rental_start_dt')
            rental_stop_date = product._context.get('rental_stop_dt')
            if not rental_start_date or not rental_stop_date:
                return 0.0

            price = product.price_compute('rental_price', uom=uom, date=date)[product.id]

            src_currency = product.currency_id or self.env.company.currency_id
            if src_currency != target_currency:
                price = src_currency._convert(price, target_currency, self.env.company, date, round=False)
            return price
        # sale flow
        return super(PricelistItem, self)._compute_base_price(product, quantity, uom, date, target_currency)

# -*- coding: utf-8 -*-

from itertools import chain

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_repr
from odoo.tools.misc import get_lang


def convert_uom_qty(quantity, default_uom, product_uom):
    uom_qty = quantity
    if default_uom:
        try:
            uom_qty = default_uom._compute_quantity(quantity, product_uom)
        except UserError:
            pass  # Ignored - incompatible UoM in context, use default product UoM
    return uom_qty


class Pricelist(models.Model):
    _inherit = 'product.pricelist'

    # ----------------------------------------------------------------------------
    # Helpers Discount
    # ----------------------------------------------------------------------------

    def get_pricelist_discount(self, base_price, list_price, product=None, date=False):
        """ Both prices are in the pricelist currency
            TODO: product argument is useless
        """
        # check if discount should be included in display price
        discount = 0.0
        price_list = list_price
        if self.discount_policy == 'without_discount':
            if list_price != 0.0:
                discount_candidate = (base_price - list_price) / base_price * 100
                if (discount_candidate > 0 and list_price > 0) or (discount_candidate < 0 and list_price < 0):  # refuse negative discount
                    discount = discount_candidate
                    price_list = base_price
                else:  # negative discounts (= surcharge) are included in the display price
                    price_list = max(base_price, list_price)
        return price_list, discount

    # ----------------------------------------------------------------------------
    # Public Rental API
    # ----------------------------------------------------------------------------

    def get_rental_list_price(self, products, start_dt, end_dt, date=False, quantity=1.0):
        """ Apply the pricelist on the rent price for the given period of given products, according to the given date, quantity and uoM.
            :param products : list of product.product on which the pricelist should be applied
            :param start_dt: rental start date
            :param end_dt: rental end date
            :returns : map product ID with rental price with pricelist applied (in pricelist currency)
        """
        product_list = [product for product in products]
        price_list = [product.rent_price_unit for product in products.with_context(rental_start_dt=start_dt, rental_end_dt=end_dt, currency_id=self.currency_id.id)]

        new_price_list = self._rental_apply_pricelist(product_list, price_list, date=date, quantity=quantity)

        result = {}
        for index, product in enumerate(product_list):
            result[product.id] = new_price_list[index]
        return result

    def apply_rental_pricelist(self, product, price_list, date=False, quantity=1.0):
        """ Apply the pricelist on the given product for the list of price, according to the given date, quantity and uoM.
            :param product : product.product on which the pricelist should be applied
            :param price_list: list of price on which the current pricelist should be applied. This is
                a list of amounts (float) expressed in the corresponding product currency.
            :returns list of converted amounts, in the same order as the iinput price_list. Result will
                be a list of amount expressed in the pricelist currency
        """
        product_list = [product] * len(price_list)
        return self._rental_apply_pricelist(product_list, price_list, date=date, quantity=quantity)

    def apply_rental_pricelist_on_template(self, product_template, price_list, date=False, quantity=1.0):
        """ Apply the pricelist on the given product template for the list of price, according to the given date, quantity and uoM.
            :param product_template : product.template on which the pricelist should be applied
            :param price_list: list of price on which the current pricelist should be applied. This is
                a list of amounts (float) expressed in the corresponding product currency.
            :returns list of converted amounts, in the same order as the input price_list. Result will
                be a list of amount expressed in the pricelist currency
        """
        product_list = [product_template.product_variant_id] * len(price_list)
        return self._rental_apply_pricelist(product_list, price_list, date=date, quantity=quantity)

    # ----------------------------------------------------------------------------
    # Private Rental Methods
    # ----------------------------------------------------------------------------

    def _rental_apply_pricelist(self, product_list, price_list, date=False, quantity=1.0, uom_id=False):
        """ Apply the pricelist on the tuple product / price related to that product, for the date, quantity and uoM given.
            :param product_list : list of product.product
            :param price_list: list of price on which the current pricelist should be applied. This is
                a list of amounts (float) expressed in the corresponding product currency.
            :returns list of converted amounts, in the same order as the iinput price_list. Result will
                be a list of amount expressed in the pricelist currency
        """
        # set date for currency
        if not date:
            date = fields.Datetime.now()

        # default UoM
        default_uom = None
        if uom_id:
            default_uom = self.env['uom.uom'].browse(uom_id)

        # get the matching rule per product
        product_rule_map = self._rental_get_product_rule_map(product_list, date, quantity, default_uom)

        # applied the rule on base price
        result = []
        for product, price in zip(product_list, price_list):
            rule = product_rule_map.get(product.id)
            if rule:
                uom_qty = convert_uom_qty(quantity, default_uom, product.uom_id)
                list_price = rule._compute_price(price, default_uom or product.uom_id, product, quantity=uom_qty)
            else:
                list_price = price
            result.append(list_price)
        return result

    def _rental_get_product_rule_map(self, product_list, date, quantity, default_uom):
        """ get the pricelist rule that should be applied on every given product. """
        relevant_rules = self._rental_find_relevant_items(product_list, date)

        result = {}
        for product in product_list:
            suitable_rule = None

            uom_qty = convert_uom_qty(quantity, default_uom, product.uom_id)

            for rule in relevant_rules:
                if rule.min_quantity and uom_qty < rule.min_quantity:  # skip too few quantity
                    continue
                if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:  # skip not matching the product template (as it will implies not matching the product)
                    continue
                if rule.product_id and product.id != rule.product_id.id:  # skip not matching the product
                    continue
                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue
                suitable_rule = rule
                break  # get out of the loop when find the first matching rule for current product

            result[product.id] = suitable_rule
        return result

    def _rental_find_relevant_items(self, product_list, date):
        """ Find the relevant priclist rules to apply to all the given product.
            Note: products might be a list of product.product or a recordset !!
            :param product_list : list or recordset of product.product to find the matching rule
            :param date : date on which the matching rule is applicable
        """
        self.ensure_one()
        # extract all category ancestors
        categ_ids = set()
        for product in product_list:
            categ = product.categ_id
            while categ:
                categ_ids.add(categ.id)
                categ = categ.parent_id
        categ_ids = list(categ_ids)

        # extract product and template IDs
        product_ids = []
        product_template_ids = []
        for product in product_list:
            product_ids.append(product.id)
            product_template_ids.append(product.product_tmpl_id.id)

        # load all rules
        # NOTE: if you change `order by` on that query, make sure it matches
        # _order from model to avoid inconstencies and undeterministic issues.
        # NOTE: quantity is not filter here, but the ordering by qty min is important for the following
        self.env['product.pricelist.item'].flush(['price', 'currency_id', 'company_id'])
        self.env.cr.execute("""
            SELECT
                item.id
            FROM
                product_pricelist_item AS item
                LEFT JOIN product_category AS categ ON item.categ_id = categ.id
            WHERE
                (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))
                AND (item.product_id IS NULL OR item.product_id = any(%s))
                AND (item.categ_id IS NULL OR item.categ_id = any(%s))
                AND (item.pricelist_id = %s)
                AND (item.date_start IS NULL OR item.date_start<=%s)
                AND (item.date_end IS NULL OR item.date_end>=%s)
                AND (item.applicable_on = 'rent')
            ORDER BY
                item.applied_on, item.min_quantity DESC, categ.complete_name DESC, item.id DESC
        """, (product_template_ids, product_ids, categ_ids, self.id, date, date))
        item_ids = [x[0] for x in self.env.cr.fetchall()]
        return self.env['product.pricelist.item'].browse(item_ids)

    # ----------------------------------------------------------------------------
    # Overrides
    # ----------------------------------------------------------------------------

    def _compute_price_rule_get_items(self, products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids, categ_ids):
        """ Override that to only return 'sale' items """
        items = super(Pricelist, self)._compute_price_rule_get_items(products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids, categ_ids)
        return items.filtered(lambda item: item.applicable_on == 'sale')


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

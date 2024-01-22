from odoo import api, fields, models


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

# -*- coding: utf-8 -*-

from odoo import fields, http, _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo.exceptions import UserError


class WebsiteShop(WebsiteSale):

    @http.route()
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        """ website_id is required in the context to compute website prices of rental tenures. """
        result = super(WebsiteShop, self).shop(page=page, category=category, search=search, ppg=ppg, **post)
        result.qcontext['products'] = result.qcontext['products'].with_context(website_id=request.website.id)
        return result

    def _prepare_product_values(self, product, category, search, **kwargs):
        """ website_id is required in the context to compute website prices of rental tenures. """
        result = super(WebsiteShop, self)._prepare_product_values(product, category, search, **kwargs)
        result['product'] = result['product'].with_context(website_id=request.website.id)
        return result

    @http.route()
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        """ Note: this is almost a copy/past of website_sale """
        if kw.get('is_rental'):
            # copy/paste of website_sale
            sale_order = request.website.sale_get_order(force_create=True)
            if sale_order.state != 'draft':
                request.session['sale_order_id'] = None
                sale_order = request.website.sale_get_order(force_create=True)

            # no variant handling

            # rental dates are required
            if not kw.get('rental_start') or not kw.get('rental_stop'):
                raise UserError(_("Rental dates are mandatory !"))

            # add rental parameters
            sale_order._cart_update(
                product_id=int(product_id),
                add_qty=add_qty,
                set_qty=set_qty,
                product_custom_attribute_values=False,
                no_variant_attribute_values=False,
                is_rental=True,
                rental_start_dt=kw['rental_start'],
                rental_end_dt=kw['rental_stop'],
            )

            # same as in website sale
            if kw.get('express'):
                return request.redirect("/shop/checkout?express=1")
            return request.redirect("/shop/cart")

        return super(WebsiteShop, self).cart_update(product_id, add_qty=add_qty, set_qty=set_qty, **kw)

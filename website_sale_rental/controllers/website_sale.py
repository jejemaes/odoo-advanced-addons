# -*- coding: utf-8 -*-

from odoo import fields, http, _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo.exceptions import UserError


class WebsiteShop(WebsiteSale):

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        response = super(WebsiteShop, self).product(product, category=category, search=search, **kwargs)
        if product.can_be_rented:
            response.qcontext.update({
                'rental_tenures': product.get_rental_tenures(request.website.pricelist_id.id)
            })
        return response

    @http.route(['/shop/cart/rental_add/'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_rental_add(self, product_id, start, stop, qty=0, resource_ids=[]):
        """ Add a rental line """
        order = request.website.sale_get_order(force_create=1)
        if order.state != 'draft':
            request.website.sale_reset()
            return False

        product = request.env['product.product'].sudo().browse(product_id)

        start_dt = fields.Datetime.from_string(start)
        stop_dt = fields.Datetime.from_string(stop)

        unavailabilities = product.rental_calendar_id.get_combined_unavailibilities(start_dt, stop_dt, resource_ids)
        for resource_id in resource_ids:
            if unavailabilities[resource_id]:
                raise UserError(_("The resource can not be rented as it is unavailable."))

        qty_or_resources = qty if product.rental_tracking == 'no' else resource_ids
        price, pricing_explanation, qty = product.website_rental_price_and_quantity(start_dt, stop_dt, qty_or_resources, request.website.currency_id)

        rental_lines = order.create_rental_line(
            product.id,
            product.uom_id.id,
            price,
            start_dt,
            stop_dt,
            quantity=qty or 0,
            resource_ids=resource_ids,
            additional_description=pricing_explanation,
        )
        return {'url': '/shop/cart'}

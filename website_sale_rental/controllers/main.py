# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pytz import timezone

import pytz

from odoo import http, fields, _, tools
from odoo.http import request
from odoo.osv import expression
from odoo.addons.resource.models.resource_mixin import timezone_datetime


class WebsiteSaleRental(http.Controller):

    @http.route('/shop/rental/<model("product.template"):product>/calendar', type='json', auth="public", website=True)
    def rental_product_calendar(self, product, start, stop):
        start_dt = timezone_datetime(fields.Datetime.from_string(start))
        stop_dt = timezone_datetime(fields.Datetime.from_string(stop))

        unavailabilities = product.sudo()._rental_get_unavalabilities(start_dt, stop_dt)
        bookings = product.sudo()._rental_get_bookings(start_dt, stop_dt)

        return {
            'unavailabilities': unavailabilities,
            'bookings': bookings,
        }

    @http.route('/shop/rental/<model("product.template"):product_tmpl>/price', type='json', auth="public", website=True)
    def rental_price_simulation(self, product_tmpl, start, stop, qty=1):
        start_dt = timezone_datetime(fields.Datetime.from_string(start))
        stop_dt = timezone_datetime(fields.Datetime.from_string(stop))
        qty = int(qty)

        # TODO use product.product directly
        product = product_tmpl.product_variant_id.sudo().with_context(lang=request.env.user.lang or 'en_US')
        pricelist = request.website.get_current_pricelist()
        partner = request.env.user.partner_id

        # resource and quantity
        error = False
        if product.rental_tracking == 'use_resource':
            if qty > product.resource_count:
                error = _("There is only %s resource to rent. You can not reserve more.") % (product.resource_count,)
            else:
                # Note: we do this in memory using `filtered` as searching on 'available' resources is not 100% working.
                resource_available_count = len(product_tmpl.sudo()._rental_get_available_resources(start, stop, qty))
                if not resource_available_count:
                    error = _("There is no resource available to rent for your period.")
                elif resource_available_count < qty:
                    error = _("There is only %s available resources to rent for your period.") % (resource_available_count,)
        elif product.rental_tracking == 'no':  # don't chekc qunatity limit as there is none
            unavalabilities = product.rental_calendar_id._unavailable_intervals(start_dt, stop_dt, resource=None, domain=None, tz=None)
            if unavalabilities:
                error = _("The rental calendar does not allow to rent this period.")

        # get unit price
        price_data = product.get_rental_price(start_dt, stop_dt, pricelist_id=pricelist.id, quantity=qty)[product.id]
        pricing_explanation = product.with_context(pricelist_id=pricelist.id).get_rental_pricing_explanation(start_dt, stop_dt, show_price=False, currency_id=request.website.pricelist_id.currency_id.id)[product.id]

        # compute amount with discount
        price = price_data['price_list'] * (1 - (price_data['discount'] or 0.0) / 100.0)

        # aplpy taxes if needed
        fpos = request.env['account.fiscal.position'].get_fiscal_position(partner.id).sudo()
        taxes = fpos.map_tax(product_tmpl.sudo().taxes_id.filtered(lambda x: x.company_id == request.website.company_id), product_tmpl, partner)
        tax_field = 'total_excluded' if request.env.user.user_has_groups('account.group_show_line_subtotals_tax_excluded') else 'total_included'
        price = taxes.compute_all(price, pricelist.currency_id, 1, product, partner)[tax_field]

        return {
            'price': tools.format_amount(request.env, price, pricelist.currency_id, request.env.context.get('lang')),
            'discount': price_data['discount'],
            'pricing_explanation': pricing_explanation,
            'error': error,
        }

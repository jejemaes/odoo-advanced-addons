# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pytz

from odoo import http, fields, _
from odoo.http import request
from odoo.osv import expression

from odoo.addons.sale_rental import tools


class WebsiteSaleRental(http.Controller):

    @http.route('/website_sale_rental/<model("product.product"):product>/calendar', type='json', auth="public")
    def rental_product_calendar(self, product, start, stop):
        start_dt = fields.Datetime.from_string(start)
        stop_dt = fields.Datetime.from_string(stop)

        return {
            'unavailabilities': product.sudo().rental_calendar_id.get_unavailabilities(start_dt, stop_dt),
            'resource_ids': product.sudo().resource_ids.ids,
        }

    @http.route('/website_sale_rental/<model("product.product"):product>/resources', type='json', auth="public")
    def rental_product_rental_booking(self, product, start, stop):
        start_dt = fields.Datetime.from_string(start)
        stop_dt = fields.Datetime.from_string(stop)
        resource_ids = product.sudo().resource_ids.ids

        domain = expression.OR([['&', ('date_from', '<=', start_dt), ('date_to', '>', start_dt)], ['&', ('date_from', '>=', start_dt), ('date_to', '<', stop_dt)]])
        domain = expression.AND([[('state', '!=', 'cancel'), ('date_from', '>=', fields.Datetime.to_string(fields.Datetime.now() - relativedelta(months=1)))], domain])
        domain = expression.AND([[('resource_id', 'in', resource_ids)], domain])
        bookings = request.env['rental.booking'].sudo().search(domain)

        rental_map = dict.fromkeys(resource_ids, list())
        for booking in bookings:
            rental_map[booking.resource_id.id].append((booking.date_from, booking.date_to, booking.state in ['reserved', 'picked_up', 'returned']))

        leave_domain = request.env['resource.calendar.leaves'].get_leave_domain()
        return {
            'unavailabilities': product.sudo().rental_calendar_id.get_combined_unavailibilities(start_dt, stop_dt, resource_ids, domain=leave_domain),
            'rental': rental_map,
        }

    @http.route(['/website_sale_rental/<model("product.product"):product>/simulate_price'], type='json', auth="public", website=True)
    def rental_price_simulation(self, product, start=False, stop=False, qty_or_res_ids=False):
        start_dt = fields.Datetime.from_string(start)
        stop_dt = fields.Datetime.from_string(stop)

        price, pricing_explanation, qty = product.sudo().website_rental_price_and_quantity(start_dt, stop_dt, qty_or_res_ids, request.website.currency_id)

        return {
            'price': tools.format_amount(request.env, price * qty, request.website.currency_id, request.env.context.get('lang')),
            'pricing_explanation': pricing_explanation if qty == 1 else _('%s * (%s)') % (qty, pricing_explanation,)
        }

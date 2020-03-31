# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_rental_timezone = fields.Selection(related='rental_calendar_id.tz')
    website_rental_timezone_offset = fields.Integer(compute='_compute_website_timezone_offset')

    @api.depends('rental_calendar_id.tz')
    def _compute_website_timezone_offset(self):
        for product in self:
            calendar_tz = product.sudo().rental_calendar_id.tz
            product.website_rental_timezone_offset = -int(datetime.now().astimezone(pytz.timezone(calendar_tz)).utcoffset().total_seconds() / 60)


class Product(models.Model):
    _inherit = 'product.product'

    def website_rental_price_and_quantity(self, start_dt, stop_dt, qty_or_res_ids, currency):

        # find correct tz and quantity
        if self.rental_tracking == 'no':
            _tz = pytz.timezone(self.env.user.tz)
            qty = qty_or_res_ids
        else:  # resource tracked
            qty = len(qty_or_res_ids)
            if len(qty_or_res_ids) == 1:
                resource = self.env['resource.resource'].sudo().browse(qty_or_res_ids[0])
                _tz = pytz.timezone(resource.tz or resource.calendar_id.tz)
            else:
                _tz = pytz.timezone(self.env.user.tz)

        # convert dates to compute price
        start_dt = pytz.utc.localize(start_dt).astimezone(_tz)
        stop_dt = pytz.utc.localize(stop_dt).astimezone(_tz)
        price, pricing_explanation = self.get_rental_price_and_details(start_dt, stop_dt, price_field='website_rent_price', currency_dst=currency)
        return price, pricing_explanation, qty

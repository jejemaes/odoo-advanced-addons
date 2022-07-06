# -*- coding: utf-8 -*-
import pytz
from datetime import datetime

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    rental_tenure_id = fields.Many2one('product.rental.tenure', compute='_compute_rental_tenure_id')
    rental_min_duration_unit = fields.Selection([
        ('hour', 'Hour(s)'),
        ('day', 'Day(s)'),
        ('week', 'Week(s)'),
        ('month', 'Month(s)'),
    ], string="Rental Min. Duration", compute='_compute_rental_min_duration')
    rental_select_overlap_mode = fields.Selection([
        ('none', "No overlap"),
        ('only_draft', "Draft renting can be selected"),
    ], default="none")
    website_rental_display_mode = fields.Selection([
        ('calendar', 'Calendar'),
        ('form', 'Form'),
    ], compute='_compute_website_rental_display_mode')
    website_rental_pricing_timezone = fields.Selection(_tz_get, string="Rental Pricing Timezone", compute='_compute_website_rental_pricing_timezone')

    # fixed price
    website_rental_base_price = fields.Float("Displayed fixed rental price without pricelist applied", compute='_compute_website_rental_base_price')
    website_rental_list_price = fields.Float("Displayed fixed rental price with pricelist applied", compute='_compute_website_rental_list_price')

    @api.depends('rental_tenure_ids')
    def _compute_rental_tenure_id(self):
        order_map = self.env['product.rental.tenure']._tenure_duration_ordering_map()
        for product in self:
            tenure_type = product.rental_tenure_type
            if tenure_type == 'weekday':
                product.rental_tenure_id = product.rental_tenure_ids.sorted(lambda t: (t.base_price, t.weekday_count), reverse=False)[:1]
            elif tenure_type == 'duration':
                tenures = product.rental_tenure_ids.sorted(lambda t: (t.base_price, order_map.get(t.duration_uom, 0), t.duration_value), reverse=False)
                product.rental_tenure_id = tenures[:1]
            else:
                product.rental_tenure_id = None

    @api.depends('rental_tenure_type', 'rental_tenure_ids')
    def _compute_rental_min_duration(self):
        order_map = self.env['product.rental.tenure']._tenure_duration_ordering_map()
        for product in self:
            if not product.rental_tenure_ids:
                product.rental_min_duration_unit = False
            else:
                if product.rental_tenure_type == 'weekday':
                    product.rental_min_duration_unit = 'day'
                elif product.rental_tenure_type == 'duration':
                    tenures = product.rental_tenure_ids.sorted(lambda t: (order_map.get(t.duration_uom, 0), t.duration_value), reverse=True)
                    product.rental_min_duration_unit = tenures[-1].duration_uom

    @api.depends('rental_tracking', 'resource_ids')
    def _compute_website_rental_display_mode(self):
        for product in self:
            if product.rental_tracking == 'no':
                product.website_rental_display_mode = 'calendar'
            else:
                if product.resource_count == 1:
                    product.website_rental_display_mode = 'calendar'
                else:
                    product.website_rental_display_mode = 'form'

    @api.depends('rental_tracking', 'resource_ids')
    def _compute_website_rental_pricing_timezone(self):
        for product in self:
            if product.rental_tracking == 'no':
                product.website_rental_pricing_timezone = product.rental_calendar_id.tz
            else:
                if product.resource_count == 1:
                    product.website_rental_pricing_timezone = product.resource_ids[:1].tz or product.resource_ids[:1].calendar_id.tz
                else:
                    product.website_rental_pricing_timezone = None

    @api.depends('rental_fixed_price')
    @api.depends_context('website_id', 'uid')
    def _compute_website_rental_base_price(self):
        website = self.env['website'].browse(self._context['website_id'])
        pricelist = website.get_current_pricelist()
        partner = self.env.user.partner_id

        tax_field = 'total_excluded' if self.user_has_groups('account.group_show_line_subtotals_tax_excluded') else 'total_included'
        fpos = self.env['account.fiscal.position'].get_fiscal_position(partner.id).sudo()

        for product_template in self:
            taxes = fpos.map_tax(product_template.sudo().taxes_id.filtered(lambda x: x.company_id == website.company_id), product_template, partner)
            base_price = product_template.currency_id._convert(product_template.rental_fixed_price, pricelist.currency_id, company=website.company_id, date=fields.Date.today())
            product_template.website_rental_base_price = taxes.compute_all(base_price, pricelist.currency_id, 1, product_template.product_variant_id, partner)[tax_field]

    @api.depends('rental_fixed_price')
    @api.depends_context('website_id', 'uid')
    def _compute_website_rental_list_price(self):
        website = self.env['website'].browse(self._context['website_id'])
        pricelist = website.get_current_pricelist()
        partner = self.env.user.partner_id

        tax_field = 'total_excluded' if self.user_has_groups('account.group_show_line_subtotals_tax_excluded') else 'total_included'
        fpos = self.env['account.fiscal.position'].get_fiscal_position(partner.id).sudo()

        price_list = [p.currency_id._convert(p.rental_fixed_price, pricelist.currency_id, company=website.company_id, date=fields.Date.today()) for p in self]
        products = [p.product_variant_id for p in self]
        converted_price_data_list = pricelist._rental_apply_pricelist(products, price_list, quantity=1.0)

        result = {}
        for product_template, base_price, list_price in zip(self, price_list, converted_price_data_list):
            price, discount = pricelist.get_pricelist_discount(base_price, list_price, product=product_template.product_variant_id, date=False)
            if discount:
                result[product_template.id] = list_price  # base price with discount applied
            else:
                result[product_template.id] = price  # base price without discount applied

        for product_template in self:
            taxes = fpos.map_tax(product_template.sudo().taxes_id.filtered(lambda x: x.company_id == website.company_id), product_template, partner)
            base_price = result.get(product_template.id, product_template.rental_fixed_price)
            product_template.website_rental_list_price = taxes.compute_all(base_price, pricelist.currency_id, 1, product_template.product_variant_id, partner)[tax_field]

    # -------------------------------------------------------------------------
    # Calendar
    # -------------------------------------------------------------------------

    def _rental_get_unavalabilities(self, start_dt, end_dt, tz=None):
        resource = None
        calendar = self.rental_calendar_id
        if self.rental_tracking == 'use_resource':
            resource = self.resource_ids[:1]
            calendar = self.resource_ids[:1].calendar_id
        unavailabilities = calendar._unavailable_intervals(start_dt, end_dt, resource=resource, domain=[('time_type', '=', 'leave')], tz=tz)  # domain is none implies not attendance + leaves
        return [(fields.Datetime.to_string(item[0]), fields.Datetime.to_string(item[1]), 'unavailability') for item in unavailabilities if item[0] != item[1]]  # remove intervals having the same start and stop

    def _rental_get_bookings(self, start_dt, end_dt):
        bookings_list = []
        if self.rental_tracking == 'use_resource' and self.resource_ids:
            resource = self.resource_ids[:1]
            bookings = self.env['rental.booking'].search([('state', '!=', 'cancel'), ('resource_id', '=', resource.id), ('date_from', '<=', end_dt), ('date_to', '>=', start_dt)])
            bookings_list = [(fields.Datetime.to_string(booking.date_from), fields.Datetime.to_string(booking.date_to), 'confirmed' if booking.state in ['reserved', 'picked_up', 'returned', 'done'] else 'draft') for booking in bookings]
        return bookings_list

    # -------------------------------------------------------------------------
    # Business
    # -------------------------------------------------------------------------

    def _rental_get_available_resources(self, start_dt, end_dt, quantity):
        """ Return the first available resources for the given dates (string, utc)
            Note: here should be immementated smart algorithm to choose resources.
            TODO: maybe this should be move to sale_rental. on product or template ?
        """
        resources = self.env['resource.resource']
        for resource in self.resource_ids.with_context(resource_start_dt=start_dt, resource_stop_dt=end_dt).filtered(lambda res: res.is_available):
            if len(resources) < quantity:
                resources |= resource
        return resources

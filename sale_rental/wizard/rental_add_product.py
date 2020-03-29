# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta
from pytz import timezone, UTC

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.sale_rental.models.product import get_timedelta


class RentalSaleItem(models.TransientModel):
    _name = 'rental.add.product'
    _description = "Add a Rental Sale Item"

    @api.model
    def default_get(self, fields):
        active_model = self._context.get('active_model')
        if active_model != 'sale.order':
            raise UserError(_('You can only apply this action from a Sales Order.'))
        result = super(RentalSaleItem, self).default_get(fields)
        if not result.get('sale_order_id'):
            result['sale_order_id'] = self._context.get('active_id')
        return result

    sale_order_id = fields.Many2one('sale.order', 'Sales Order', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='sale_order_id.currency_id')
    partner_id = fields.Many2one('res.partner', string='Customer', related="sale_order_id.partner_id")

    product_id = fields.Many2one('product.product', 'Rental Product', required=True, domain=[('can_be_rented', '=', True)])
    product_qty = fields.Float("Quantity", default=1)
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    product_rental_tracking = fields.Selection(related='product_id.rental_tracking')
    product_rental_min_duration = fields.Selection(related='product_id.rental_min_duration')

    price_unit = fields.Monetary("Unit Price", compute='_compute_rental_price', help="Price for the renting period per rented object.")
    pricing_explanation = fields.Text("Pricing explanation", compute='_compute_rental_price', help="Helper text to understand rental price computation.")

    datetime_from = fields.Datetime("Start Datetime", required=True)
    datetime_to = fields.Datetime("End Datetime", required=True)
    date_from = fields.Date("Start Date")
    date_to = fields.Date("End Date")
    date_warning = fields.Text("Date Warning", compute='_compute_date_warning')

    resource_ids = fields.Many2many('resource.resource', 'rental_add_product_resource_line', string='Resources', help="Take available resource")
    resource_count = fields.Integer("Resource Quantity", compute='_compute_resource_count')
    resource_warning = fields.Text("Resource availibility message", compute='_compute_resource_warning')

    @api.depends('product_id', 'datetime_from', 'datetime_to')
    def _compute_rental_price(self):
        for wizard in self:
            if wizard.product_id and wizard.datetime_from and wizard.datetime_to:
                if wizard.datetime_from <= wizard.datetime_to:
                    price, pricing_explanation = wizard.product_id.get_rental_price_and_details(wizard.datetime_from, wizard.datetime_to, currency_dst=self.currency_id)

                    wizard.pricing_explanation = pricing_explanation
                    wizard.price_unit = price
                else:
                    wizard.pricing_explanation = False
                    wizard.price_unit = 0.0
            else:
                wizard.pricing_explanation = False
                wizard.price_unit = 0.0

    @api.depends('product_id', 'datetime_from', 'datetime_to')
    def _compute_date_warning(self):
        for wizard in self:
            msg = False
            if wizard.product_id and wizard.datetime_from and wizard.datetime_to:
                start_dt = fields.Datetime.from_string(wizard.datetime_from)
                stop_dt = fields.Datetime.from_string(wizard.datetime_to)
                if stop_dt < start_dt + get_timedelta(1, wizard.product_id.rental_min_duration):
                    msg = _("The minimum rental duration must be greater than 1 %s") % (dict(wizard.product_id._fields['rental_min_duration']._description_selection(self.env))[wizard.product_id.rental_min_duration],)
            wizard.date_warning = msg

    @api.depends('resource_ids')
    def _compute_resource_count(self):
        for wizard in self:
            wizard.resource_count = len(wizard.resource_ids)

    @api.depends('resource_ids', 'datetime_from', 'datetime_to')
    def _compute_resource_warning(self):
        for wizard in self:
            message_items = []
            if wizard.datetime_from and wizard.datetime_to:
                resource_unavailability_map = wizard.resource_ids.get_unavailable_intervals(wizard.datetime_from, wizard.datetime_to)
                for resource in wizard.resource_ids:
                    unavailable_intervals = resource_unavailability_map.get(resource.id, [])
                    if unavailable_intervals:
                        message = _('%s is not available') % (resource.name,)
                        message_interval_items = []
                        for start, stop in unavailable_intervals:
                            message_interval_items.append(_('from %s to %s') % (start, stop))  #(tools.format_date(self.env, start), tools.format_date(self.env, stop)))
                        message += _(' (%s)') % (', '.join(message_interval_items))
                        message_items.append(message)
            wizard.resource_warning = '\n'.join(message_items)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            self.date_from = False
            self.date_to = False
            self.datetime_from = False
            self.datetime_to = False

        result = {'domain': {}}
        if self.product_id.rental_tracking == 'use_resource':
            self.product_qty = 0
            result['domain']['resource_ids'] = [('product_id', '=', self.product_id.id)]
        return result

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        tz_user = self.env.user.tz or 'UTC'
        if self.date_from:
            date_from = fields.Date.from_string(self.date_from)
            self.datetime_from = timezone(tz_user).localize(datetime.datetime.combine(date_from, datetime.time.min)).astimezone(UTC).replace(tzinfo=None)
        else:
            self.datetime_from = False
        if self.date_to:
            date_to = fields.Date.from_string(self.date_to)
            self.datetime_to = timezone(tz_user).localize(datetime.datetime.combine(date_to, datetime.time.max).replace(microsecond=0) + timedelta(seconds=1)).astimezone(UTC).replace(tzinfo=None)
        else:
            self.datetime_to = False

    @api.onchange('datetime_from', 'datetime_to', 'product_id')
    def _onchange_resources_lines(self):
        if self.product_id.rental_tracking == 'use_resource':
            if self.datetime_from and self.datetime_to:
                self.resource_line_ids = False
                lines = []
                for resource in self.product_id.resource_ids:
                    lines.append((0, 0, {
                        'resource_id': resource.id,
                    }))
                self.resource_line_ids = lines
            else:
                self.resource_line_ids = False

    @api.constrains('product_id', 'resource_ids')
    def _check_product_rental_policy(self):
        for wizard in self:
            if wizard.product_id.rental_tracking == 'use_resource' and not wizard.resource_ids:
                raise ValidationError(_('Rental product %s needs at least one of its resource selected to be rented.') % (wizard.product_id.name))

    # ----------------------------------------------------------------------------
    # Actions
    # ----------------------------------------------------------------------------

    def action_add_line(self):
        for wizard in self:
            # create the SOL
            product_id = wizard.product_id.id
            uom_id = wizard.product_uom_id.id

            wizard.sale_order_id.create_rental_line(
                product_id, uom_id,
                wizard.price_unit,
                wizard.datetime_from,
                wizard.datetime_to,
                resource_ids=wizard.resource_ids.ids,
                quantity=wizard.product_qty or 0,
                additional_description=wizard.pricing_explanation,
            )
        return False

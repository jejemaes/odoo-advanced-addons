# -*- coding: utf-8 -*-
import math

from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.resource_advanced.models.resource import timezone_datetime


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    can_be_rented = fields.Boolean('Can be Rented', default=False, help="Specify if the product can be rent in a sales order line.", copy=True)
    description_rental = fields.Text('Rental Description', translate=True, help="A description of the Product to rent it.")
    rental_tenure_type = fields.Selection([
        ('duration', 'Any Duration'),
        ('weekday', 'Per Week Day'),
    ], string="Tenure Duration", default=False, copy=True)
    rental_tenure_ids = fields.One2many('product.rental.tenure', 'product_template_id', string="Rental Tenures", copy=True)
    rental_tracking = fields.Selection([
        ('no', 'No Tracking'),
        ('use_resource', 'Track Individual Items'),
    ], string="Tracking Type", default=False, copy=True)
    rental_agreement_id = fields.Many2one('rental.agreement', "Rental Agreement")
    rental_calendar_id = fields.Many2one("resource.calendar", string="Rental Calendar")
    rental_tz = fields.Selection(_tz_get, string='Timezone', default=lambda self: self._context.get('tz') or self.env.user.tz or 'UTC')

    resource_ids = fields.One2many('resource.resource', 'product_template_id', string="Resources", domain=[('resource_type', '=', 'material')])
    resource_count = fields.Integer("Resource Count", compute='_compute_resource_count')

    rental_padding_before = fields.Float("Before Security Time", default=0, copy=True, help="Expressed in hours")
    rental_padding_after = fields.Float("After Security Time", default=0, copy=True, help="Expressed in hours")

    _sql_constraints = [
        ('rental_tenure_type_required', "CHECK((can_be_rented='t' AND rental_tenure_type IS NOT NULL) OR (can_be_rented = 'f'))", 'A rental product needs a rental tenure type.'),
        ('rental_tracking_required', "CHECK((can_be_rented='t' AND rental_tracking IS NOT NULL) OR (can_be_rented = 'f'))", 'A rental product needs a rental tracking.'),
        ('rental_calendar_required', "CHECK((rental_tracking = 'no' AND rental_calendar_id IS NOT NULL) OR (rental_tracking != 'no'))", 'A rental product without tracking needs a rental calendar.'),
        ('rental_tz_required', "CHECK((rental_tracking = 'use_resource' AND rental_tz IS NOT NULL) OR (rental_tracking != 'use_resource'))", 'A rental product with tracking needs a rental timezone.'),
    ]

    @api.depends('resource_ids')
    def _compute_resource_count(self):
        grouped_data = self.env['resource.resource'].sudo().read_group([('product_template_id', 'in', self.ids)], ['product_template_id'], ['product_template_id'])
        mapped_data = {db['product_template_id'][0]: db['product_template_id_count'] for db in grouped_data}
        for product in self:
            product.resource_count = mapped_data.get(product.id, 0)

    @api.onchange('can_be_rented')
    def _onchange_can_be_rented(self):
        if not self.can_be_rented:
            self.rental_tenure_type = None
            self.rental_tenure_ids = [(5, 0)]
            self.rental_tracking = None
        else:
            self.rental_tenure_type = 'duration'
            self.rental_tracking = 'no'

    @api.onchange('type')
    def _onchange_service_for_rental(self):
        if self.type == 'service':
            if self.can_be_rented:
                self.rental_tracking = 'no'
            else:
                self.rental_tracking = False

    @api.onchange('rental_tenure_type')
    def _onchange_rental_tenure_type(self):
        if self.rental_tenure_type == 'weekday':
            weekdays = self.env['resource.day'].get_all_days()
            self.rental_tenure_ids = [(5, 0)] + [(0, 0, {'weekday_ids': [(6, 0, [weekday.id])], 'base_price': 1.0}) for weekday in weekdays]
        elif self.rental_tenure_type == 'duration':
            self.rental_tenure_ids = [
                (5, 0),
                (0, 0, {'duration_uom': 'hour', 'duration_value': 1, 'base_price': 1.0}),
                (0, 0, {'duration_uom': 'day', 'duration_value': 1, 'base_price': 1.0}),
            ]

    @api.onchange('rental_tracking')
    def _onchange_rental_tracking(self):
        if self.rental_tracking == 'use_resource':
            self.rental_calendar_id = None
        if self.rental_tracking == 'no':
            self.rental_tz = None
            self.rental_padding_before = False
            self.rental_padding_after = False

    @api.constrains('type', 'can_be_rented', 'rental_tracking')
    def _check_service_for_rental(self):
        for product in self:
            if product.type == 'service':
                if product.can_be_rented and product.rental_tracking != 'no':
                    raise ValidationError("A rentable service can not be tracked.")
                if not product.can_be_rented and product.rental_tracking:
                    raise ValidationError("A non-rentable service can not be tracked.")

    # ----------------------------------------------------------------------------
    # Business Methods
    # ----------------------------------------------------------------------------

    def _get_rental_timezone(self):
        if self.rental_tracking == 'no':
            return self.rental_calendar_id.tz
        if self.rental_tracking == 'use_resource':
            return self.rental_tz
        return 'UTC'

    def get_rental_price_and_details(self, start_dt, end_dt, pricelist, quantity=1, currency=False, uom_id=False, date_order=False):
        # timezone given dates and convert them to product rental tz
        start_dt = timezone_datetime(start_dt)
        end_dt = timezone_datetime(end_dt)

        # convert into product timezome to compute price
        tz = timezone(self._get_rental_timezone())
        start_dt = start_dt.astimezone(tz)
        end_dt = end_dt.astimezone(tz)

        currency = currency if currency else self.currency_id

        combinaison, price = self.rental_tenure_ids.with_context(
            quantity=quantity,
            uom_id=uom_id,
            date_order=date_order
        )._rental_price_combinaison(start_dt, end_dt, currency_dst=currency)
        return price, self.env['product.rental.tenure']._get_human_pricing_details(combinaison, currency_dst=currency)

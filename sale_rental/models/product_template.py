# -*- coding: utf-8 -*-
import math

from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.resource_advanced.models.resource import timezone_datetime
from odoo.tools.date_utils import add, subtract, start_of, end_of


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

        combinaison, price = self.with_context(
            quantity=quantity,
            uom_id=uom_id,
            date_order=date_order
        )._rental_price_combinaison(start_dt, end_dt, currency_dst=currency)
        return price, self._rental_get_human_pricing_details(combinaison, currency_dst=currency)

    # ----------------------------------------------------------------------------
    # Tenure API
    # ----------------------------------------------------------------------------

    def _rental_price_combinaison(self, start_dt, end_dt, currency_dst=False):
        """ Compute the rental price unit in the given currency for the given period.
            :param start_dt : timezoned datetime representing the beginning of the rental period
            :param end_dt : timezoned datetime representing the end of the rental period
            :param currency_dst : currency record
        """
        if not self.rental_tenure_ids:
            return {}, 0.0
        # TODO check sart/end are timezoned
        tenure_type = self.rental_tenure_type
        if hasattr(self, '_tenure_%s_price_combinaison' % (tenure_type,)):
            return getattr(self, '_tenure_%s_price_combinaison' % (tenure_type,))(start_dt, end_dt, currency_dst=currency_dst)
        raise NotImplementedError

    @api.model
    def _rental_get_human_pricing_details(self, combinaison_map, currency_dst=False):
        if not combinaison_map:
            return _("Free")
        tenure_type = self.rental_tenure_type
        if hasattr(self, '_tenure_%s_get_human_pricing_details' % (tenure_type,)):
            return getattr(self, '_tenure_%s_get_human_pricing_details' % (tenure_type,))(combinaison_map, currency_dst=currency_dst)
        raise NotImplementedError()

    #
    # Duration Tenure
    #

    def _tenure_duration_price_combinaison(self, start_dt, end_dt, currency_dst=False):
        assert start_dt <= end_dt, "Start dates must be before the end date."

        order_map = self.env['product.rental.tenure']._tenure_duration_ordering_map()

        if not self.rental_tenure_ids:
            return {}, 0.0

        tenures = self.rental_tenure_ids.sorted(lambda t: (order_map.get(t.duration_uom, 0), t.duration_value), reverse=True)

        cost = 0.0
        combinaison = []
        for tenure in tenures:

            if start_dt < end_dt:
                is_last = tenure == tenures[-1]
                delta = tenure._get_tenure_timedelta()

                # fill period with current rental uom
                while start_dt + delta <= end_dt:
                    combinaison.append(tenure.id)
                    start_dt += delta
                    if currency_dst:
                        cost += tenure.currency_id._convert(tenure.rent_price, currency_dst, tenure.product_template_id.company_id or self.env.company, fields.Date.today())
                    else:
                        cost += tenure.rent_price

                # if the last tenure uom period is started, then count it entirely
                if is_last and start_dt < end_dt:
                    combinaison.append(tenure.id)
                    start_dt += delta
                    if currency_dst:
                        cost += tenure.currency_id._convert(tenure.rent_price, currency_dst, tenure.product_template_id.company_id or self.env.company, fields.Date.today())
                    else:
                        cost += tenure.rent_price

        # transform into a map tenure.id -> number of time it is used
        tenure_occurence = {}
        for tenure_id in combinaison:
            tenure_occurence.setdefault(tenure_id, 0)
            tenure_occurence[tenure_id] += 1

        return tenure_occurence, cost

    @api.model
    def _tenure_duration_rental_get_human_pricing_details(self, combinaison_map, currency_dst=False):
        """ transform the number of occurence of given tenure into a computation readable for human beings. """
        tenures = self.env['product.rental.tenure'].browse(combinaison_map.keys())
        tenure_map = {tenure.id: tenure for tenure in tenures}

        computation_members = []
        for tenure_id, occurence in combinaison_map.items():
            tenure = tenure_map[tenure_id]
            if currency_dst:
                price = tenure.currency_id._convert(tenure.rent_price, currency_dst, tenure.product_template_id.company_id or self.env.company, fields.Date.today())
            else:
                price = tenure.rent_price
            computation_members.append(_("%s * %s (%s)") % (occurence, tenure.tenure_name, self.env['product.rental.tenure']._display_price(price, tenure.currency_id, currency_dst)))
        return _(' + ').join(computation_members)

    #
    # Weekday Tenure
    #

    def _tenure_weekday_price_combinaison(self, start_dt, end_dt, currency_dst=False):
        assert start_dt <= end_dt, "Start dates must be before the end date."

        tzinfo = start_dt.tzinfo
        start_dt = start_of(start_dt, 'day').replace(tzinfo=tzinfo)
        end_dt = end_of(end_dt, 'day').replace(tzinfo=tzinfo)

        cost = 0.0
        combinaison = []
        while start_dt < end_dt:
            applicable_tenures = self.rental_tenure_ids.filtered(lambda t: t.weekday_start == start_dt.weekday() + 1)
            if applicable_tenures:
                tenure = applicable_tenures._tenure_weekday_find_best_tenure(start_dt, end_dt)
                combinaison.append(tenure.id)
                if currency_dst:
                    cost += tenure.currency_id._convert(tenure.rent_price, currency_dst, tenure.product_template_id.company_id or self.env.company, fields.Date.today())
                else:
                    cost += tenure.rent_price
                start_dt += tenure._get_tenure_timedelta()
            else:
                start_dt += relativedelta(days=1) # one day free to continue the way to stop dt

        # transform into a map tenure.id -> number of time it is used
        tenure_occurence = {}
        for tenure_id in combinaison:
            tenure_occurence.setdefault(tenure_id, 0)
            tenure_occurence[tenure_id] += 1
        return tenure_occurence, cost

    @api.model
    def _tenure_weekday_rental_get_human_pricing_details(self, combinaison_map, currency_dst=False):
        """ transform the number of occurence of given tenure into a computation readable for human beings. """
        tenures = self.env['product.rental.tenure'].browse(combinaison_map.keys())
        tenure_map = {tenure.id: tenure for tenure in tenures}

        computation_members = []
        for tenure_id, occurence in combinaison_map.items():
            tenure = tenure_map[tenure_id]
            if currency_dst:
                price = tenure.currency_id._convert(tenure.rent_price, currency_dst, tenure.product_template_id.company_id or self.env.company, fields.Date.today())
            else:
                price = tenure.rent_price
            computation_members.append(_("%s * %s (%s)") % (occurence, tenure.tenure_name, self.env['product.rental.tenure']._display_price(price, tenure.currency_id, currency_dst)))
        return _(' + ').join(computation_members)

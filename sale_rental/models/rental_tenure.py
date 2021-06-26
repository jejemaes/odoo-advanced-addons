# -*- coding: utf-8 -*-
import functools
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import add, subtract, start_of, end_of
from odoo import tools


class ProductRentalTenure(models.Model):
    _name = 'product.rental.tenure'
    _description = "Rental Price"
    _order = 'sequence, id'

    product_template_id = fields.Many2one('product.template', "Product", required=True)
    tenure_name = fields.Char("Tenure Name", compute='_compute_tenure_name')
    tenure_type = fields.Selection(related='product_template_id.rental_tenure_type', store=True)
    currency_id = fields.Many2one('res.currency', "Currency", related='product_template_id.currency_id')
    base_price = fields.Monetary("Base Rent Price", required=True, default=1)
    rent_price = fields.Float("Rent Price", compute='_compute_rent_price', help="This amount is expressed in the currency of the pricelist, or (fallback) in product currency.")
    sequence = fields.Integer("Sequence", default=5)

    duration_value = fields.Integer("Tenue")
    duration_uom = fields.Selection([
        ('hour', 'Hour(s)'),
        ('day', 'Day(s)'),
        ('week', 'Week(s)'),
        ('month', 'Month(s)'),
    ], string="Unit")

    weekday_ids = fields.Many2many('resource.day', 'rental_tenure_resource_day_rel', 'rental_tenure_id', 'resource_day_id', "Weekdays")
    weekday_selectable_ids = fields.Many2many('resource.day', compute='_compute_weekday_selectable_ids')
    weekday_count = fields.Integer("Number of Weekdays", compute='_compute_weekday_count')
    weekday_start = fields.Integer("Start of Weekday", compute='_compute_weekday_start')

    _sql_constraints = [
        ('base_price_positive', 'CHECK(base_price >= 0)', "The rent price must be positive."),
        ('duration_combinaition', 'UNIQUE(product_template_id, duration_value, duration_uom)', "A product can not have multi tenure defined for the same duration."),
        ('duration_valure_required_tenure_type', "CHECK((tenure_type = 'duration' AND duration_value IS NOT NULL) OR (tenure_type != 'duration'))", "A duration value is required for a tenure of 'duration' type."),
        ('duration_uom_required_tenure_type', "CHECK((tenure_type = 'duration' AND duration_uom IS NOT NULL) OR (tenure_type != 'duration'))", "A duration UoM is required for a tenure of 'duration' type."),
    ]

    @api.depends('tenure_type', 'duration_uom', 'duration_value', 'weekday_ids')
    @api.depends_context('lang')
    def _compute_tenure_name(self):
        for tenure in self:
            if tenure.tenure_type == 'duration':
                tenure.tenure_name = '%s %s' % (tenure.duration_value, dict(self._fields['duration_uom']._description_selection(self.env))[tenure.duration_uom])
            elif tenure.tenure_type == 'weekday':
                tenure.tenure_name = ', '.join(tenure.sudo().weekday_ids.mapped('shortname'))
            else:
                tenure.tenure_name = False

    @api.depends('base_price')
    @api.depends_context('pricelist_id', 'quantity', 'date_order')
    def _compute_rent_price(self):
        """ This will show the price for one unit of the tenure, with the pricelist (if given in context) applied. No tax is applied here. """
        pricelist_id = self._context.get('pricelist_id', False)
        date_order = self._context.get('date_order', False)

        tenure_price_map = {}  # if no pricelist, this map is not updated

        pricelist = None
        if pricelist_id:
            pricelist = self.env['product.pricelist'].browse(pricelist_id)

            price_data_map = self._get_pricelist_price_data(pricelist, date=date_order)
            for tenure in self:
                tenure_price_map[tenure.id] = price_data_map[tenure.id]['price_list']

        for tenure in self:
            tenure.rent_price = tenure_price_map.get(tenure.id, tenure.base_price)

    @api.depends('weekday_ids')
    def _compute_weekday_selectable_ids(self):
        resource_days = self.env['resource.day'].get_all_days()
        for tenure in self:
            tenure_dayofweeks = tenure.weekday_ids.mapped('dayofweek')
            if tenure_dayofweeks:
                effective_dayofweeks = [item - 1 for item in tenure_dayofweeks]  # DoW in range [0-6]
                effective_dayofweeks_neigbor_tuples = [[dof-1, dof+1] for dof in effective_dayofweeks] # list of tuple with neighbors index
                effective_dayofweeks_neigbors = functools.reduce(lambda a, b: a + b, effective_dayofweeks_neigbor_tuples) # list of tuple to simple list
                dayofweeks_neigbors = [(item % 7) + 1 for item in effective_dayofweeks_neigbors]  # modulo 7 and back to DoW of odoo (not datetime lib)
                tenure.weekday_selectable_ids = resource_days.filtered(lambda d: d.dayofweek in dayofweeks_neigbors)
            else:
                tenure.weekday_selectable_ids = resource_days # all can be selected

    @api.depends('weekday_ids')
    def _compute_weekday_count(self):
        for tenure in self:
            tenure.weekday_count = len(tenure.weekday_ids)

    @api.depends('weekday_ids')
    def _compute_weekday_start(self):
        # TODO : find a better algorithm
        dayofweeks = self.env['resource.day'].get_all_days()

        for tenure in self:
            tenure_weekofdays = tenure.weekday_ids.mapped('dayofweek')
            dayofweek_current = min(tenure_weekofdays)
            while dayofweek_current:
                # decrease and cycle
                dayofweek_current = dayofweek_current - 1
                if dayofweek_current == 0:
                    dayofweek_current = 7
                # stop when find the first WoD no linked to tenure
                if dayofweek_current not in tenure_weekofdays:
                    break

            # plus one, since we have at least one loop in while loop
            # modulo 7, beause monday alone as day will get out of loop with value 8
            tenure.weekday_start = (dayofweek_current + 1) % 7 if dayofweek_current != 6 else 7

    @api.onchange('tenure_type')
    def _onchange_tenure_type(self):
        if self.tenure_type == 'weekday':
            self.duration_value = None
            self.duration_uom = None
        if self.tenure_type == 'duration':
            self.weekday_ids = None

    @api.constrains('tenure_type', 'weekday_ids', 'duration_value', 'duration_uom')
    def _check_rental_type(self):
        for tenure in self:
            if tenure.tenure_type == 'weekday':
                if not tenure.weekday_ids:
                    raise ValidationError(_("At least one day musmt be selected for the tenure."))
            if tenure.tenure_type == 'duration':
                if not tenure.duration_value:
                    raise ValidationError(_("The duration is required on the tenure."))
                if not tenure.duration_uom:
                    raise ValidationError(_("The duration unit is required on the tenure."))

    @api.constrains('weekday_ids')
    def _check_weekday_ids(self):
        for tenure in self:
            tenure_dayofweeks = tenure.weekday_ids.mapped('dayofweek')
            if tenure_dayofweeks:

                effective_dayofweeks = [item - 1 for item in tenure_dayofweeks]  # DoW are from 0 to 6 (incl.)
                start_dayofweek = min(effective_dayofweeks)

                partition = []
                current_dayofweek = start_dayofweek
                while current_dayofweek not in partition:
                    partition.append(current_dayofweek)

                    current_dayofweek = current_dayofweek - 1
                    current_dayofweek = current_dayofweek % 7  # Note: -1 % 7 = 6

                    if current_dayofweek not in effective_dayofweeks:
                        break

                current_dayofweek = start_dayofweek + 1 # since start_dayofweek is already in partition
                while current_dayofweek not in partition:
                    partition.append(current_dayofweek)

                    current_dayofweek = current_dayofweek + 1
                    current_dayofweek = current_dayofweek % 7

                    if current_dayofweek not in effective_dayofweeks:  # TODO maybe this should the loop condition
                        break

                if set(effective_dayofweeks) - set(partition):
                    day_names = tenure.weekday_ids.mapped('name')
                    raise ValidationError(_("The chosen days must all be consecutives. %s are not.") % (','.join(day_names)))

    def name_get(self):
        res = []
        for tenure in self:
            res.append((tenure.id, tenure.tenure_name))
        return res

    # ----------------------------------------------------------------------------
    # Pricing Helper Methods
    # ----------------------------------------------------------------------------

    def _get_pricelist_price_data(self, pricelist, date=False):
        """ Get pricelist data (unit price, base price and discount) for one unit of given tenure. All amounts here
            are converted in pricelist currency.
            :param pricelist : product.pricelist record to apply on tenure price
            :returns a dict with tenure ID as key, and the following dict as value such as:
                'price_base': the converted price in PL currency
                'price_list': price with the currency applied
                'discount': percentage of discount that should be applied on 'price_base' to get 'price_list'
        """
        result = {}
        tenure_product_map = dict.fromkeys(self.mapped('product_template_id'), self.env['product.rental.tenure'])
        for tenure in self:
            tenure_product_map[tenure.product_template_id] |= tenure

        for product_template, tenures in tenure_product_map.items():
            sorted_tenures = tenures.sorted(key=lambda r: r.id)
            price_list = [t.base_price for t in sorted_tenures]

            converted_price_data_list = pricelist.apply_rental_pricelist_on_template(product_template, price_list, date=date, quantity=1.0)
            for tenure, price_data in zip(sorted_tenures, converted_price_data_list):
                result[tenure.id] = price_data

        return result

    # ----------------------------------------------------------------------------
    # Helper Methods
    # ----------------------------------------------------------------------------

    @api.model
    def _display_price(self, price, from_currency, to_currency=False):
        currency = to_currency or from_currency
        return tools.format_amount(self.env, price, currency, self.env.context.get('lang'))

    def _get_tenure_timedelta(self):
        if self.tenure_type == 'weekday':
            return relativedelta(days=self.weekday_count)
        if self.tenure_type == 'duration':
            unit = self.duration_uom
            factor = self.duration_value or 1
            if unit == 'minute':
                return relativedelta(minutes=factor)
            if unit == 'hour':
                return relativedelta(hours=factor)
            if unit == 'day':
                return relativedelta(days=factor)
            if unit == 'week':
                return relativedelta(weeks=factor)
            if unit == 'month':
                return relativedelta(months=factor)
            return None
        raise NotImplementedError()

    @api.model
    def _tenure_duration_ordering_map(self):
        """ get the map responsible for the order to apply when computing rental price """
        return {
            'hour': 10,
            'day': 20,
            'week': 30,
            'month': 40,
        }

    def _tenure_weekday_find_best_tenure(self, start, stop):
        applicable_tenures = self.sorted(lambda t: t.weekday_count, reverse=True)

        for tenure in applicable_tenures:
            # minus one second bacuase a day is from 00:00:00 to 23:59:59,99999 accordting to start_of/end_of
            if start + tenure._get_tenure_timedelta() - relativedelta(seconds=1) <= stop:
                return tenure
        return applicable_tenures[-1]  # the last is the less worth

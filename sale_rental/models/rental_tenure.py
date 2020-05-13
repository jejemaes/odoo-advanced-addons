# -*- coding: utf-8 -*-

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.sale_rental.models.product import get_timedelta
from odoo.addons.sale_rental import tools


class AbstractRentalTenure(models.AbstractModel):
    _name = 'rental.tenure.abstract'
    _description = "Abstract Rental Tenue"

    product_template_id = fields.Many2one('product.template', "Product", required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='product_template_id.currency_id')
    rent_price = fields.Monetary("Rent Price", required=True, default=1)
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")

    def _rental_price_combinaison(self, start_dt, end_dt, price_field='rent_price', currency_dst=False):
        raise NotImplementedError()

    @api.model
    def _get_human_pricing_details(self, combinaison_map, price_field='rent_price', currency_dst=False):
        raise NotImplementedError()

    def display_price(self, price, from_currency, to_currency=False):
        currency = to_currency or from_currency
        return tools.format_amount(self.env, price, currency, self.env.context.get('lang'))


class RentalTenureDuration(models.Model):
    _name = 'rental.tenure.duration'
    _inherit = 'rental.tenure.abstract'
    _description = "Rental Tenure"
    _order = 'sequence DESC, tenure_value ASC'

    tenure_value = fields.Integer("Tenue", required=True, default=1)
    rental_uom = fields.Selection([
        ('day', 'Day(s)'),
        ('week', 'Week(s)'),
        ('month', 'Month(s)'),
    ], string="Unit", required=True, default='day')
    sequence = fields.Integer("Sequence", default=5)

    _sql_constraints = [
        ('tenure_value_positive', 'CHECK (tenure_value > 0)', "The tenure must be positive."),
        ('rent_price_positive', 'CHECK (rent_price >= 0)', "The rent price must be positive."),
        ('unique_per_pricelist', 'UNIQUE(product_template_id, pricelist_id)', "The rent price must be unique per pricelist.")
    ]

    def name_get(self):
        result = []
        for tenure in self:
            tenure_name = _('%s %s') % (tenure.tenure_value, dict(self._fields['rental_uom']._description_selection(self.env))[tenure.rental_uom])
            result.append((tenure.id, tenure_name))
        return result

    # ----------------------------------------------------------------------------
    # Business Methods
    # ----------------------------------------------------------------------------

    def _rental_price_combinaison(self, start_dt, end_dt, price_field='rent_price', currency_dst=False):
        assert start_dt <= end_dt, "Start dates must be before the end date."

        order_map = self._get_ordering_map()

        if not self:
            return {}, 0.0

        tenures = self.sorted(lambda t: (order_map.get(t.rental_uom, 0), t.tenure_value), reverse=True)

        cost = 0.0
        combinaison = []
        for tenure in tenures:

            if start_dt < end_dt:
                is_last = tenure == tenures[-1]
                delta = tenure._get_timedelta()

                # fill period with current rental uom
                while start_dt + delta <= end_dt:
                    combinaison.append(tenure.id)
                    start_dt += delta
                    if currency_dst:
                        cost += tenure.currency_id._convert(tenure[price_field], currency_dst, tenure.product_template_id.company_id, fields.Date.today())
                    else:
                        cost += tenure[price_field]

                # if the last tenure uom period is started, then count it entirely
                if is_last and start_dt < end_dt:
                    combinaison.append(tenure.id)
                    start_dt += delta
                    if currency_dst:
                        cost += tenure.currency_id._convert(tenure[price_field], currency_dst, tenure.product_template_id.company_id, fields.Date.today())
                    else:
                        cost += tenure[price_field]

        # transform into a map tenure.id -> number of time it is used
        tenure_occurence = {}
        for tenure_id in combinaison:
            tenure_occurence.setdefault(tenure_id, 0)
            tenure_occurence[tenure_id] += 1

        return tenure_occurence, cost

    @api.model
    def _get_human_pricing_details(self, combinaison_map, price_field='rent_price', currency_dst=False):
        """ transform the number of occurence of given tenure into a computation readable for human beings. """
        tenures = self.env['rental.tenure.duration'].browse(combinaison_map.keys())
        tenure_map = {tenure.id: tenure for tenure in tenures}

        computation_members = []
        for tenure_id, occurence in combinaison_map.items():
            tenure = tenure_map[tenure_id]
            if currency_dst:
                price = tenure.currency_id._convert(tenure[price_field], currency_dst, tenure.product_template_id.company_id, fields.Date.today())
            else:
                price = tenure[price_field]
            computation_members.append(_("%s * %s (%s)") % (occurence, tenure.display_name, self.display_price(price, tenure.currency_id, currency_dst)))
        return _(' + ').join(computation_members)

    def _get_timedelta(self):
        factor = int(self.tenure_value) or 1
        return get_timedelta(factor, self.rental_uom)

    @api.model
    def _get_ordering_map(self):
        """ get the map responsible for the order to apply when computing rental price """
        return {
            'day': 20,
            'week': 30,
            'month': 40,
        }


class RentalTenureDay(models.Model):
    _name = 'rental.tenure.day'
    _inherit = 'rental.tenure.abstract'
    _description = "Rental Tenure Day"
    _order = 'day_count ASC, weekday_start ASC'

    monday = fields.Boolean("Mon.", default=False)
    tuesday = fields.Boolean("Tue.", default=False)
    wednesday = fields.Boolean("Wed.", default=False)
    thursday = fields.Boolean("Thu.", default=False)
    friday = fields.Boolean("Fri.", default=False)
    saturday = fields.Boolean("Sat.", default=False)
    sunday = fields.Boolean("Sun.", default=False)
    day_count = fields.Integer("Number of Days", compute='_compute_day_count', store=True)
    weekday_start = fields.Integer("Start of Weekday", compute='_compute_weekday_start', store=True)

    # TODO https://dba.stackexchange.com/questions/9759/postgresql-multi-column-unique-constraint-and-null-values
    _sql_constraints = [
        ('rent_price_positive', 'CHECK (rent_price >= 0)', "The rent price must be positive."),
        ('rent_unique_days_and_pricelist', 'UNIQUE (product_template_id, pricelist_id, monday, thursday, wednesday, tuesday, friday, saturday, sunday)', "The tenure must be unique."),
    ]

    def name_get(self):
        abbreviation_map = self._get_day_abbreviation()
        result = []
        for tenure in self:
            tenure_day_names = []
            for fname, weight in tenure._get_day_weight_map().items():
                if weight:
                    tenure_day_names.append(abbreviation_map[fname])
            result.append((tenure.id, ' ,'.join(tenure_day_names)))
        return result

    @api.depends('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    def _compute_day_count(self):
        for tenure in self:
            days_weight = tenure._get_day_weight_map().values()
            tenure.day_count = sum(days_weight)

    @api.depends('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    def _compute_weekday_start(self):
        day_field_list = self._get_day_fields()
        for tenure in self:
            weekday_start = 0
            for index, fname in enumerate(day_field_list):
                prev_index = index - 1 if index - 1 >= 0 else len(day_field_list) - 1
                prev_day_fname = day_field_list[prev_index]
                if tenure[fname] and not tenure[prev_day_fname]:
                    weekday_start = index + 1
            tenure.weekday_start = weekday_start

    @api.constrains('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
    def _check_selected_days(self):
        days = 2 * [index for index, value in enumerate(self._get_day_fields())]
        for tenure in self:
            tenure_days = [index for index, fname in enumerate(self._get_day_fields()) if tenure[fname]]

            if not tenure_days:
                raise ValidationError(_('The tenure line must have at least one day selected.'))

            possibilities = []
            for index, fname in enumerate(self._get_day_fields()):
                current = days[index:index + tenure.day_count]
                current.sort()
                possibilities.append(current)

            if tenure_days not in possibilities:
                raise ValidationError(_('The selected days must form a continuous slot.'))

    # ----------------------------------------------------------------------------
    # Business Methods
    # ----------------------------------------------------------------------------

    def _rental_price_combinaison(self, start_dt, end_dt, price_field='rent_price', currency_dst=False):
        assert start_dt <= end_dt, "Start dates must be before the end date."

        cost = 0.0
        combinaison = []
        while start_dt < end_dt:
            applicable_tenures = self.filtered(lambda t: t.weekday_start == start_dt.weekday() +1)
            if applicable_tenures:
                tenure = applicable_tenures._find_best_tenure(start_dt, end_dt)
                combinaison.append(tenure.id)
                if currency_dst:
                    cost += tenure.currency_id._convert(tenure[price_field], currency_dst, tenure.product_template_id.company_id, fields.Date.today())
                else:
                    cost += tenure[price_field]
                start_dt += tenure._get_timedelta()
            else:
                start_dt += relativedelta(days=1) # one day free to continue the way to stop dt

        # transform into a map tenure.id -> number of time it is used
        tenure_occurence = {}
        for tenure_id in combinaison:
            tenure_occurence.setdefault(tenure_id, 0)
            tenure_occurence[tenure_id] += 1
        return tenure_occurence, cost

    @api.model
    def _get_human_pricing_details(self, combinaison_map, price_field='rent_price', currency_dst=False):
        """ transform the number of occurence of given tenure into a computation readable for human beings. """
        tenures = self.env['rental.tenure.day'].browse(combinaison_map.keys())
        tenure_map = {tenure.id: tenure for tenure in tenures}

        computation_members = []
        for tenure_id, occurence in combinaison_map.items():
            tenure = tenure_map[tenure_id]
            if currency_dst:
                price = tenure.currency_id._convert(tenure[price_field], currency_dst, tenure.product_template_id.company_id, fields.Date.today())
            else:
                price = tenure[price_field]
            computation_members.append(_("%s * %s (%s)") % (occurence, tenure.display_name, self.display_price(price, tenure.currency_id, currency_dst)))
        return _(' + ').join(computation_members)

    def _get_timedelta(self):
        return relativedelta(days=self.day_count)

    def _find_best_tenure(self, start, stop):
        applicable_tenures = self.sorted(lambda t: t.day_count, reverse=True)
        for tenure in applicable_tenures:
            if start + tenure._get_timedelta() <= stop:
                return tenure
        return applicable_tenures[-1]  # the last is the less worth

    @api.model
    def _get_day_fields(self):
        return ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    @api.model
    def _get_day_abbreviation(self):
        return {
            'monday': _('Monday'),
            'tuesday': _('Tuesday'),
            'wednesday': _('Wednesday'),
            'thursday': _('Thursday'),
            'friday': _('Friday'),
            'saturday': _('Saturday'),
            'sunday': _('Sunday'),
        }

    @api.model
    def _get_weekday_map(self):
        return {
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6,
            'sunday': 7,
        }

    def _get_day_weight_map(self):
        day_field_list = self._get_day_fields()

        result = dict.fromkeys(day_field_list, 0)
        for fname in day_field_list:
            if self[fname]:
                result[fname] = 1
        return result

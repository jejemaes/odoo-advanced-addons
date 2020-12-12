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
    rent_price = fields.Monetary("Rent Price", compute='_compute_rent_price')
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
                tenure.tenure_name = ', '.join(tenure.weekday_ids.mapped('shortname'))
            else:
                tenure.tenure_name = False

    @api.depends('base_price')
    @api.depends_context('pricelist_id', 'quantity', 'uom_id', 'date_order')
    def _compute_rent_price(self):
        # TODO here we must start the pricelist integeration
        pricelist_id = self._context.get('pricelist_id', False)
        currency_id = self._context.get('currency_id', False)
        quantity = self._context.get('quantity', 1)
        uom_id = self._context.get('uom_id', False)
        date_order = self._context.get('date_order', False)

        for tenure in self:
            currency = self.env['res.currency'].browse(currency_id)
            tenure.rent_price = tenure.base_price

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
    # Common Methods
    # ----------------------------------------------------------------------------

    def _rental_price_combinaison(self, start_dt, end_dt, currency_dst=False):
        if not self:
            return {}, 0.0
        # TODO check sart/end are timezoned
        tenure_type = self.mapped('tenure_type')[0]
        if hasattr(self, '_tenure_%s_price_combinaison' % (tenure_type,)):
            return getattr(self, '_tenure_%s_price_combinaison' % (tenure_type,))(start_dt, end_dt, currency_dst=currency_dst)
        raise NotImplementedError

    @api.model
    def _get_human_pricing_details(self, combinaison_map, currency_dst=False):
        if not combinaison_map:
            return _("Free")
        tenures = self.env['product.rental.tenure'].browse(combinaison_map.keys())  # TODO api.model here is not usefull to find the tenure type to get the method to execute
        tenure_type = tenures.mapped('tenure_type')[0]
        if hasattr(self, '_tenure_%s_get_human_pricing_details' % (tenure_type,)):
            return getattr(self, '_tenure_%s_get_human_pricing_details' % (tenure_type,))(combinaison_map, currency_dst=currency_dst)
        raise NotImplementedError()

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

    # ----------------------------------------------------------------------------
    # Duration Tenure
    # ----------------------------------------------------------------------------

    def _tenure_duration_price_combinaison(self, start_dt, end_dt, currency_dst=False):
        assert start_dt <= end_dt, "Start dates must be before the end date."

        order_map = self._tenure_duration_ordering_map()

        if not self:
            return {}, 0.0

        tenures = self.sorted(lambda t: (order_map.get(t.duration_uom, 0), t.duration_value), reverse=True)

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
    def _tenure_duration_get_human_pricing_details(self, combinaison_map, currency_dst=False):
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
            computation_members.append(_("%s * %s (%s)") % (occurence, tenure.tenure_name, self._display_price(price, tenure.currency_id, currency_dst)))
        return _(' + ').join(computation_members)

    @api.model
    def _tenure_duration_ordering_map(self):
        """ get the map responsible for the order to apply when computing rental price """
        return {
            'hour': 10,
            'day': 20,
            'week': 30,
            'month': 40,
        }

    # ----------------------------------------------------------------------------
    # Day Tenure
    # ----------------------------------------------------------------------------

    def _tenure_weekday_price_combinaison(self, start_dt, end_dt, currency_dst=False):
        assert start_dt <= end_dt, "Start dates must be before the end date."

        tzinfo = start_dt.tzinfo
        start_dt = start_of(start_dt, 'day').replace(tzinfo=tzinfo)
        end_dt = end_of(end_dt, 'day').replace(tzinfo=tzinfo)

        cost = 0.0
        combinaison = []
        while start_dt < end_dt:
            applicable_tenures = self.filtered(lambda t: t.weekday_start == start_dt.weekday() + 1)
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
    def _tenure_weekday_get_human_pricing_details(self, combinaison_map, currency_dst=False):
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
            computation_members.append(_("%s * %s (%s)") % (occurence, tenure.tenure_name, self._display_price(price, tenure.currency_id, currency_dst)))
        return _(' + ').join(computation_members)

    def _tenure_weekday_find_best_tenure(self, start, stop):
        applicable_tenures = self.sorted(lambda t: t.weekday_count, reverse=True)

        for tenure in applicable_tenures:
            # minus one second bacuase a day is from 00:00:00 to 23:59:59,99999 accordting to start_of/end_of
            if start + tenure._get_tenure_timedelta() - relativedelta(seconds=1) <= stop:
                return tenure
        return applicable_tenures[-1]  # the last is the less worth

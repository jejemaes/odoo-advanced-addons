# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.resource_advanced.models.resource import timezone_datetime


def get_timedelta(factor, unit):
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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _default_rental_tenure_day_ids(self):
        return [
            (5, 0, 0),
            (0, 0, {'monday': True, 'rent_price': 1}),
            (0, 0, {'tuesday': True, 'rent_price': 1}),
            (0, 0, {'wednesday': True, 'rent_price': 1}),
            (0, 0, {'thursday': True, 'rent_price': 1}),
            (0, 0, {'friday': True, 'rent_price': 1}),
            (0, 0, {'saturday': True, 'rent_price': 1}),
            (0, 0, {'sunday': True, 'rent_price': 1}),
            (0, 0, {'saturday': True, 'sunday': True, 'rent_price': 1}),
        ]

    can_be_rented = fields.Boolean('Can be Rented', default=False, help="Specify if the product can be rent in a sales order line.", copy=True)
    description_rental = fields.Text('Rental Description', translate=True, help="A description of the Product to rent it.")
    rental_tenure_type = fields.Selection([
        ('duration', 'Rent By Any Duration'),
        ('day', 'Rent Only per Day'),
    ], string="Rental Period", default=False, copy=True)
    rental_tenure_duration_ids = fields.One2many('rental.tenure.duration', 'product_template_id', string="Rental Tenures (Durations)", copy=True)
    rental_tenure_day_ids = fields.One2many('rental.tenure.day', 'product_template_id', string="Rental Tenures (Days)", copy=True)
    rental_tracking = fields.Selection([
        ('no', 'No Tracking'),
        ('use_resource', 'Track Individual Items'),
    ], string="Tracking Type", default=False, copy=True)
    resource_ids = fields.One2many('resource.resource', 'product_template_id', string="Resources", domain=[('resource_type', '=', 'material')])
    rental_agreement_id = fields.Many2one('rental.agreement', "Rental Agreement")
    rental_calendar_id = fields.Many2one("resource.calendar", string="Rental Calendar")

    rental_min_duration = fields.Selection([
        ('hour', 'Hour(s)'),
        ('day', 'Day(s)'),
        ('week', 'Week(s)'),
        ('month', 'Month(s)'),
    ], string="Rental Min. Duration", compute='_compute_rental_min_duration')
    rental_padding_before = fields.Float("Before Security Time", default=0, copy=True)
    rental_padding_after = fields.Float("After Security Time", default=0, copy=True)

    rental_product_ids = fields.Many2many('product.product', string="Additionnal Services", domain=[('type', '=', 'service'), ('sale_ok', '=', True), ('can_be_rented', '=', False)])

    _sql_constraints = [
        ('rental_tenure_type_required', "CHECK((can_be_rented='t' AND rental_tenure_type IS NOT NULL) OR (can_be_rented = 'f'))", 'A rental product needs a rental tenure type.'),
        ('rental_tracking_required', "CHECK((can_be_rented='t' AND rental_tracking IS NOT NULL) OR (can_be_rented = 'f'))", 'A rental product needs a rental tracking.'),
        ('rental_calendar_required', "CHECK((can_be_rented='t' AND rental_calendar_id IS NOT NULL) OR (can_be_rented = 'f'))", 'A rental product needs a rental calendar.'),
    ]

    resource_count = fields.Integer("Resource Count", compute='_compute_resource_count')

    @api.depends('resource_ids')
    def _compute_resource_count(self):
        grouped_data = self.env['resource.resource'].sudo().read_group([('product_template_id', 'in', self.ids)], ['product_template_id'], ['product_template_id'])
        mapped_data = {db['product_template_id'][0]: db['product_template_id_count'] for db in grouped_data}
        for product in self:
            product.resource_count = mapped_data.get(product.id, 0)

    @api.depends('rental_tenure_type', 'rental_tenure_duration_ids')
    # TODO JEM: depends_context('pricelist_id') in v13.0
    def _compute_rental_min_duration(self):
        for product in self:
            if product.rental_tenure_type == 'day':
                product.rental_min_duration = 'day'
            elif product.rental_tenure_type == 'duration':
                order_map = self.env['rental.tenure.duration']._get_ordering_map()
                tenures = product.get_rental_tenures(pricelist_id=self._context.get('pricelist_id', False))
                tenures = tenures.sorted(lambda t: (order_map.get(t.rental_uom, 0), t.tenure_value), reverse=True)
                if tenures:
                    product.rental_min_duration = tenures[-1].rental_uom
                else:
                    product.rental_min_duration = False

    @api.constrains('rental_tenure_duration_ids', 'rental_tenure_day_ids')
    def _check_can_be_rented(self):
        for product in self:
            if product.can_be_rented:
                if self.rental_tenure_type == 'duration' and not product.rental_tenure_duration_ids:
                    raise ValidationError(_('The rental product %s must have at least one tenure') % (product.name,))
                if self.rental_tenure_type == 'day' and not product.rental_tenure_day_ids:
                    raise ValidationError(_('The rental product %s must have at least one tenure') % (product.name,))

    @api.constrains('rental_product_ids', 'can_be_rented')
    def _check_addtionnal_products(self):
        for product in self:
            if product.can_be_rented and product.rental_product_ids:
                if any(p.type != 'service' and not p.can_be_rented for p in product.rental_product_ids):
                    raise ValidationError(_('The rental product %s can only have no rentable services as additional product.') % (product.name,))

    @api.onchange('can_be_rented')
    def _onchange_can_be_rented(self):
        if not self.can_be_rented:
            self.rental_tenure_type = False
            self.rental_tenure_duration_ids = [(5, 0)]
            self.rental_tenure_day_ids = [(5, 0)]
            self.rental_tracking = False
            self.rental_product_ids = [(5, 0)]
        else:
            self.rental_tenure_type = 'duration'
            self.rental_tracking = 'no'

    @api.onchange('rental_tenure_type')
    def _onchange_rental_tenure_type(self):
        if self.rental_tenure_type == 'duration':
            self.rental_tenure_day_ids = False
        elif self.rental_tenure_type == 'day':
            self.rental_tenure_duration_ids = False
            if not self.rental_tenure_day_ids:
                self.rental_tenure_day_ids = self._default_rental_tenure_day_ids()

    # ----------------------------------------------------------------------------
    # Business Methods
    # ----------------------------------------------------------------------------

    def get_rental_tenures(self, pricelist_id=False):
        # TODO JEM: filter tenues for pricelist
        if self.rental_tenure_type == 'duration':
            return self.rental_tenure_duration_ids
        if self.rental_tenure_type == 'day':
            return self.rental_tenure_day_ids


class Product(models.Model):
    _inherit = 'product.product'

    resource_ids = fields.One2many('resource.resource', 'product_id', string='Resources', domain=[('resource_type', '=', 'material')])
    resource_count = fields.Integer("Resource Count", compute='_compute_resource_count')

    @api.depends('resource_ids')
    def _compute_resource_count(self):
        grouped_data = self.env['resource.resource'].sudo().read_group([('product_id', 'in', self.ids)], ['product_id'], ['product_id'])
        mapped_data = {db['product_id'][0]: db['product_id_count'] for db in grouped_data}
        for product in self:
            product.resource_count = mapped_data.get(product.id, 0)

    @api.onchange('can_be_rented')
    def _onchange_can_be_rented(self):
        self.product_tmpl_id._onchange_can_be_rented()

    @api.onchange('rental_tenure_type')
    def _onchange_rental_tenure_type(self):
        self.product_tmpl_id._onchange_rental_tenure_type()

    @api.onchange('rental_tracking')
    def _onchange_rental_trakcing(self):
        if not self.rental_tracking:
            self.resource_ids = False

    @api.model
    def create(self, values):
        if 'resource_ids' in values:
            self = self.with_context(default_resource_type='material')
        return super(Product, self).create(values)

    def write(self, values):
        if 'resource_ids' in values:
            self = self.with_context(default_resource_type='material')
        return super(Product, self).write(values)

    # ----------------------------------------------------------------------------
    # Rental Pricing Methods
    # ----------------------------------------------------------------------------

    def get_rental_price_and_details(self, start_dt, end_dt, pricelist_id=False, price_field='rent_price', currency_dst=False):
        # timezone given dates and convert them to product rental tz
        start_dt = timezone_datetime(start_dt)
        end_dt = timezone_datetime(end_dt)
        start_dt = start_dt.astimezone(timezone(self.rental_calendar_id.tz or 'utc'))
        end_dt = end_dt.astimezone(timezone(self.rental_calendar_id.tz or 'utc'))

        tenures = self.product_tmpl_id.get_rental_tenures(pricelist_id)
        combinaison, price = tenures._rental_price_combinaison(start_dt, end_dt, price_field=price_field, currency_dst=currency_dst)
        return price, self.env[tenures._name]._get_human_pricing_details(combinaison, price_field=price_field, currency_dst=currency_dst)

    def get_rental_paddings_timedelta(self):
        before_padding = divmod(self.rental_padding_before, 60)
        after_padding = divmod(self.rental_padding_after, 60)
        return {
            'before': relativedelta(hours=before_padding[0], minutes=before_padding[1]),
            'after': relativedelta(hours=after_padding[0], minutes=after_padding[1]),
        }

    def get_product_multiline_description_sale(self):
        name = super(Product, self).get_product_multiline_description_sale()
        if self.can_be_rented and not self.sale_ok:
            name = self.display_name
        if self.description_rental:
            name += '\n' + self.description_rental
        return name

    # ----------------------------------------------------------------------------
    # Rental Calendar Methods
    # ----------------------------------------------------------------------------

    def get_rental_calendar_unavailibilities(self, start_dt, end_dt, resource_ids):
        # check reources belongs to product
        if not all(resource_id in self.resource_ids.ids for resource_id in resource_ids):
            raise UserError(_("The resource must be linked to the product when fetching their unavailablities"))
        # get calendar differences
        return self.rental_calendar_id.get_combined_unavailibilities(start_dt, end_dt, resource_ids)

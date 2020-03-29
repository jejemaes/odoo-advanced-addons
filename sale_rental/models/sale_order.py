# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from odoo.osv import expression
from odoo.addons.sale_rental.models.product import get_timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    rental_count = fields.Integer("Number of Rental Bookings", compute='_compute_rental_count')
    rental_booking_ids = fields.One2many('rental.booking', 'sale_order_id', string="Rental Bookings")

    @api.depends('rental_booking_ids')
    def _compute_rental_count(self):
        self.env.cr.execute("""
            SELECT L.order_id AS sale_order_id, count(R.id) AS rental_count
            FROM sale_order_line L
                LEFT JOIN rental_booking R ON R.sale_line_id = L.id
            WHERE L.order_id IN %s
            GROUP BY L.order_id
        """, (tuple(self.ids),))
        raw_data = self.env.cr.dictfetchall()
        mapping = {item['sale_order_id']: item['rental_count'] for item in raw_data}
        for order in self:
            order.rental_count = mapping.get(order.id, 0)

    # ---------------------------------------------------------
    # Actions
    # ---------------------------------------------------------

    def action_view_rental(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rental Bookings'),
            'domain': [('sale_line_id', 'in', self.order_line.ids)],
            'views': [(False, 'ganttdhx'), (False, 'kanban'), (False, 'tree'), (False, 'form')],
            'view_mode': 'gantt,kanban,tree,form',
            'res_model': 'rental.booking',
        }

    def action_add_rental_line(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Rental Line'),
            'views': [(False, 'form')],
            'view_mode': 'form',
            'res_model': 'rental.add.product',
            'context': {
                'active_id': self.id,
                'active_model': self._name,
            },
            'target': 'new',
        }

    def _action_confirm(self):
        """ On SO confirmation, some lines should generate a task or a project. """
        result = super(SaleOrder, self)._action_confirm()
        self.mapped('order_line').filtered(lambda l: l.is_rental).sudo().with_context(
            default_company_id=self.company_id.id,
            force_company=self.company_id.id,
        )._rental_booking_generation()
        return result

    def action_quotation_send(self):
        result = super(SaleOrder, self).action_quotation_send()

        rental_agreements = self.order_line.filtered(lambda l: l.is_rental).mapped('product_id.rental_agreement_id')
        if rental_agreements:
            result['context']['default_attachment_ids'] = [(6, 0, rental_agreements.mapped('attachment_id').ids)]

        return result

    # ---------------------------------------------------------
    # Create rental sale line
    # ---------------------------------------------------------

    def create_rental_line(self, product_id, uom_id, price_unit, rental_start_date, rental_stop_date, quantity=False, resource_ids=False, additional_description=False, **kwargs):
        """ Genrate the rental sale line with given parameters: Either `quantity` or `resource_ids` must be given.
            It also generate sale lines for additional product.
            :return sale_lines: all newly created sale.order.line recordset
        """
        product = self.env['product.product'].browse(product_id).with_context(lang=self.partner_id.lang)
        quantity = quantity if product.rental_tracking != 'use_resource' else len(resource_ids)

        # check minimal rental duration duration
        rental_start_date = fields.Datetime.from_string(rental_start_date)
        rental_stop_date = fields.Datetime.from_string(rental_stop_date)
        if rental_stop_date < rental_start_date + get_timedelta(1, product.rental_min_duration):
            raise UserError(_("The minimum rental duration must be greater than 1 %s") % (dict(product._fields['rental_min_duration']._description_selection(self.env))[product.rental_min_duration],))

        # prepare the rental sale line
        sale_line_values = self._prepare_rental_line_values(product, uom_id, quantity, price_unit, rental_start_date, rental_stop_date, additional_description, resource_ids=resource_ids, **kwargs)
        sale_lines = self.env['sale.order.line'].create(sale_line_values)

        # adds additional lines
        sale_lines_value_list = []
        for additional_product in product.rental_product_ids:
            sale_lines_value_list.append(self._prepare_rental_addional_line_values(additional_product, sale_lines))
        if sale_lines_value_list:
            sale_lines |= self.env['sale.order.line'].create(sale_lines_value_list)

        # add taxes
        sale_lines._compute_tax_id()

        return sale_lines

    def _prepare_rental_line_values(self, product, uom_id, quantity, price_unit, rental_start_date, rental_stop_date, additional_description, resource_ids=False, **kwargs):
        description = product.get_product_multiline_description_sale()
        if additional_description:
            description += '\n' + additional_description
        values = {
            'is_rental': True,
            'order_id': self.id,
            'product_id': product.id,
            'product_uom': uom_id,
            'product_uom_qty': quantity or 1.0,
            'price_unit': price_unit,
            'name': description,
            'rental_start_date': rental_start_date,
            'rental_stop_date': rental_stop_date,
        }
        if resource_ids:
            values['resource_ids'] = [(6, 0, resource_ids)]
        return values

    def _prepare_rental_addional_line_values(self, product, origin_sale_line):
        return {
            'order_id': self.id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1.0,
            'is_rental': False,
            'price_unit': product.lst_price,
            'name': product.get_product_multiline_description_sale(),
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_delivered_method = fields.Selection(selection_add=[('rental', 'Rentings')])
    rental_booking_ids = fields.One2many('rental.booking', 'sale_line_id', string="Rental Bookings", states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=False)
    resource_ids = fields.Many2many('resource.resource', 'sale_order_line_resource_rel', 'sale_line_id', 'resource_id', string='Resources')
    is_rental = fields.Boolean("Is a rental", default=False)
    rental_start_date = fields.Datetime("Rental Start Date")
    rental_stop_date = fields.Datetime("Rental End Date")

    _sql_constraints = [
        ('rental_start_date_required_for_rental', "CHECK((is_rental='t' AND rental_start_date IS NOT NULL) or (is_rental = 'f'))", 'A rental sale item requires a start date.'),
        ('rental_stop_date_required_for_rental', "CHECK((is_rental='t' AND rental_stop_date IS NOT NULL) or (is_rental = 'f'))", 'A rental sale item requires a stop date.'),
    ]

    @api.depends('product_id', 'is_rental')
    def _compute_qty_delivered_method(self):
        """ Sale Rental module compute delivered qty for product that can be rented on rental SO line """
        super(SaleOrderLine, self)._compute_qty_delivered_method()
        for line in self:
            if line.is_rental and line.product_id.can_be_rented and line.product_id.rental_tracking == 'use_resource':
                line.qty_delivered_method = 'rental'

    @api.depends('rental_booking_ids.state')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        lines_by_rental = self.filtered(lambda sol: sol.qty_delivered_method == 'rental')
        mapping = lines_by_rental._get_delivered_quantity_by_rental([('state', 'in', ['picked_up', 'returned', 'done'])])
        for line in lines_by_rental:
            line.qty_delivered = mapping.get(line.id, 0.0)

    # TODO JEM : commmented be cause it prevent to add sale line on confirmed order
    # @api.constrains('rental_booking_ids', 'is_rental')
    # def _check_rental_booking_ids(self):
    #     for line in self:
    #         if line.product_id.can_be_rented and line.is_rental:
    #             if line.state in ['sale', 'done']:
    #                 if line.product_id.rental_tracking == 'use_resource':
    #                     if not line.rental_booking_ids:
    #                         raise ValidationError(_('The Sale Item should be linked to rental bookings as the product is tracked for Rentings.'))
    #                     if line.product_id not in line.rental_booking_ids.mapped('product_id'):
    #                         raise ValidationError(_('The Sale Item should be linked to rental order having the same product %s.') % (line.product_id.name))
    #                 if line.product_id.rental_tracking == 'no':
    #                     if line.rental_booking_ids:
    #                         raise ValidationError(_('The Sale Item should not be linked to rental bookings as the product is no tracked for Rentings.'))

    @api.constrains('product_uom_qty', 'product_id', 'is_rental')
    def _check_rental_product_qty(self):
        for line in self:
            if line.is_rental and line.product_id.can_be_rented and line.product_id.rental_tracking == 'use_resource':
                if line.product_uom_qty != len(line.resource_ids):
                    raise ValidationError(_("The ordered quantity should be the same as the total of rented resources, as the rental product track its items."))

    def _get_delivered_quantity_by_rental(self, additional_domain):
        """ Compute and write the delivered quantity of current SO lines, based on their related rental orders
            :param additional_domain: domain to restrict rental order to include in computation
        """
        result = {}
        # Avoid recomputation if no SO lines concerned
        if not self:
            return result

        # Group rental by so line
        domain = expression.AND([[('sale_line_id', 'in', self.ids)], additional_domain])
        data = self.env['rental.booking'].read_group(domain, ['sale_line_id'], ['sale_line_id'], lazy=False)
        for item in data:
            sale_line_id = item['sale_line_id'][0]
            result[sale_line_id] = item['__count']

        return result

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        for line in lines:
            if line.state == 'sale' and not line.is_expense and line.is_rental:
                line.sudo()._rental_booking_generation()
        return lines

    # ---------------------------------------------------------
    # Create rental stuff
    # ---------------------------------------------------------

    def _rental_booking_generation(self):
        # reserve the existing bookings (this use case should not be existing as sale_line_id is readonly on bookings)
        self.mapped('rental_booking_ids').action_reserve()
        # create the new ones
        rental_booking_value_list = []
        for line in self.filtered('is_rental'):
            if line.product_id.rental_tracking == 'use_resource' and not line.rental_booking_ids:
                for resource in line.resource_ids:
                    rental_booking_value_list.append(line._rental_booking_prepare_values(resource.id))
        return self.env['rental.booking'].create(rental_booking_value_list)

    def _rental_booking_prepare_values(self, resource_id):
        paddings = self.product_id.get_rental_paddings_timedelta()
        return {
            'sale_line_id': self.id,
            'name': self.order_id.name,
            'resource_id': resource_id,
            'date_from': self.rental_start_date + paddings['before'],
            'date_to': self.rental_stop_date + paddings['after'],
            'sale_order_id': self.order_id.id,
            'partner_id': self.order_partner_id.id,
            'partner_shipping_id': self.order_id.partner_shipping_id.id,
            'user_id': self.order_id.user_id.id,
            'state': 'reserved',
            'agreement_id': self.product_id.rental_agreement_id.id if self.product_id.rental_agreement_id else False,
        }

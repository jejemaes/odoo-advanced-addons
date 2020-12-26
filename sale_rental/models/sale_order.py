# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.osv import expression
from odoo import tools


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    rental_count = fields.Integer("Number of Rental Bookings", compute='_compute_rental_count')
    rental_booking_ids = fields.One2many('rental.booking', 'sale_order_id', string="Rental Bookings")
    rental_line_count = fields.Integer(compute='_compute_rental_line_count')

    @api.depends('rental_booking_ids')
    def _compute_rental_count(self):
        grouped_data = self.env['rental.booking'].read_group([('sale_order_id', 'in', self.ids)], ['sale_order_id'], ['sale_order_id'])
        mapped_data = {db['sale_order_id'][0]: db['sale_order_id_count'] for db in grouped_data}
        for order in self:
            order.rental_count = mapped_data.get(order.id, 0)

    @api.depends('order_line.is_rental')
    def _compute_rental_line_count(self):
        for order in self:
            order.rental_line_count = len(order.order_line.filtered(lambda l: l.is_rental))

    def update_prices(self):
        super(SaleOrder, self).update_prices()

        lines_to_update = []
        for line in self.order_line.filtered(lambda line: line.is_rental):
            pricing_data = line.product_id.get_rental_price(line.rental_start_date, line.rental_stop_date, self.pricelist_id.id, quantity=line.product_uom_qty)
            discount = pricing_data[line.product_id.id]['discount']
            price_unit = self.env['account.tax']._fix_tax_included_price_company(pricing_data[line.product_id.id]['price_list'], line.product_id.taxes_id, line.tax_id, self.company_id)

            lines_to_update.append((1, line.id, {'price_unit': price_unit, 'discount': discount}))
        self.update({'order_line': lines_to_update})

    # ---------------------------------------------------------
    # Actions
    # ---------------------------------------------------------

    def action_view_rental(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rental Bookings'),
            'domain': [('sale_line_id', 'in', self.order_line.ids)],
            'views': [(False, 'gantt'), (False, 'kanban'), (False, 'tree'), (False, 'form')],
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

    def action_generate_rental_booking(self):
        self.mapped('order_line').filtered('is_rental')._rental_booking_generation()
        return True

    def action_draft(self):
        """ When resetting the SO, the none picked up bookings should be reset too """
        result = super(SaleOrder, self).action_draft()
        self.mapped('order_line').filtered(lambda l: l.is_rental).mapped('rental_booking_ids').sudo().filtered(lambda b: b.state != 'picked_up').action_reset()
        return result

    def action_quotation_send(self):
        result = super(SaleOrder, self).action_quotation_send()

        rental_agreements = self.order_line.filtered(lambda l: l.is_rental).mapped('product_id.rental_agreement_id')
        if rental_agreements:
            result['context']['default_attachment_ids'] = [(6, 0, rental_agreements.mapped('attachment_id').ids)]

        return result

    def _action_confirm(self):
        """ On SO confirmation, create missing bookings and reserve all bookings (existings and new ones) """
        result = super(SaleOrder, self)._action_confirm()
        rental_sale_lines = self.mapped('order_line').filtered(lambda l: l.is_rental)

        rental_sale_lines.sudo()._rental_booking_generation()
        rental_sale_lines.mapped('rental_booking_ids').sudo().filtered(lambda b: b.state == 'draft').action_reserve()
        return result

    def action_cancel(self):
        """ When cancelling the SO, the none picked up bookings should be cancelled too """
        result = super(SaleOrder, self).action_cancel()
        self.mapped('order_line').filtered(lambda l: l.is_rental).mapped('rental_booking_ids').sudo().filtered(lambda b: b.state != 'picked_up').action_cancel()
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_delivered_method = fields.Selection(selection_add=[('rental', 'Rentings')])
    is_rental = fields.Boolean("Is a rental", default=False)
    resource_ids = fields.Many2many('resource.resource', 'sale_order_line_resource_rel', 'sale_line_id', 'resource_id', string='Resources', domain="[('is_available', '=', True), ('product_id', '=', product_id)]")

    rental_start_date = fields.Datetime("Rental Start Date")
    rental_stop_date = fields.Datetime("Rental End Date")
    rental_booking_ids = fields.One2many('rental.booking', 'sale_line_id', string="Rental Bookings", states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=False)
    rental_pricing_explanation = fields.Text("Pricing explanation", compute='_compute_rental_pricing_explanation', help="Helper text to understand rental price computation.")

    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string="Product UoM")
    product_rental_tracking = fields.Selection(related='product_id.rental_tracking')

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

    @api.depends('product_id', 'rental_start_date', 'rental_stop_date')
    def _compute_rental_pricing_explanation(self):
        for line in self:
            if line.product_id and line.rental_start_date and line.rental_stop_date:
                if line.rental_start_date <= line.rental_stop_date:
                    pricing_explanation_map = line.product_id.with_context(lang=self.order_partner_id.lang or 'en_US').get_rental_pricing_explanation(line.rental_start_date, line.rental_stop_date, currency_id=self.currency_id.id)
                    line.rental_pricing_explanation = pricing_explanation_map[line.product_id.id]
                else:
                    line.rental_pricing_explanation = False
            else:
                line.rental_pricing_explanation = False

    @api.onchange('is_rental')
    def _onchange_is_rental(self):
        if self.is_rental:
            return {
                'domain': {
                    'product_id': [('can_be_rented', '=', True)]
                }
            }

    @api.onchange('resource_ids')
    def _onchange_resource_ids(self):
        if self.product_rental_tracking == 'use_resource':
            self.product_uom_qty = len(self.resource_ids)

    @api.onchange('product_id', 'rental_start_date', 'rental_stop_date', 'product_uom_qty', 'product_uom_qty')
    def product_id_change(self):
        """ Override to apply the most changes required in rental case. Purpose is to completely split flow (sale vs rental) to avoid
            patching use case flow. As counterpart, this required to copy/paste some common actions (taxes, description, ...) since
            odoo standart does not have many hooks ...
        """
        result = {}
        if self.is_rental:
            # set UoM (required field)
            if not self.product_uom or self.product_id.uom_id != self.product_uom:
                self.product_uom = self.product_id.uom_id

            # transfer the relevant taxes from product to SO line
            self._compute_tax_id()

            # compute price for the period
            if self.rental_start_date and self.rental_stop_date:
                qty = self.product_uom_qty or 0
                if self.product_id.rental_tracking == 'use_resource':
                    qty = len(self.resource_ids)

                pricing_data = self.product_id.get_rental_price(self.rental_start_date, self.rental_stop_date, self.order_id.pricelist_id.id, quantity=qty)
                self.discount = pricing_data[self.product_id.id]['discount']
                self.price_unit = self.env['account.tax']._fix_tax_included_price_company(pricing_data[self.product_id.id]['price_list'], self.product_id.taxes_id, self.tax_id, self.company_id)

                # update the line description
                self.name = self.with_context(lang=self.order_id.partner_id.lang).get_sale_order_line_multiline_description_sale(self.product_id)

            # auto set the one resource
            if self.product_id.rental_tracking == 'use_resource' and self.rental_start_date and self.rental_stop_date:
                if self.product_id.resource_count == 1:
                    print(self.product_id.resource_ids.with_context(resource_start_dt=self.rental_start_date, resource_stop_dt=self.rental_stop_date).filtered(lambda res: res.is_available))
                    self.resource_ids = self.product_id.resource_ids.with_context(resource_start_dt=self.rental_start_date, resource_stop_dt=self.rental_stop_date).filtered(lambda res: res.is_available)
        else:
            result = super(SaleOrderLine, self).product_id_change()
        return result

    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id')  # need to decorate
    def _onchange_discount(self):
        """ Note: for rental the discount is set by the `product_id_change` method """
        if self.is_rental:
            return
        return super(SaleOrderLine, self)._onchange_discount()

    @api.onchange()
    def product_uom_change(self):
        """ Note: for UoM in the rental case, it will be set by the `product_id_change` method """
        if not self.is_rental:
            return super(SaleOrderLine, self).product_uom_change()

    @api.constrains('is_rental', 'product_id')
    def _check_is_rental(self):
        for line in self:
            if line.is_rental and not line.product_id.can_be_rented:
                raise ValidationError(_("A rental sale line must be linked to a rental product."))

    @api.constrains('resource_ids')
    def _check_resource_ids(self):
        for line in self:
            if line.is_rental:
                if line.product_id.rental_tracking == 'use_resource':
                    if not line.resource_ids:
                        raise ValidationError(_('The Sale Item should be linked to resources as the product is tracked for rentings.'))
                if line.product_id.rental_tracking == 'no':
                    if line.resource_ids:
                        raise ValidationError(_('The Sale Item should not be linked to resources as the product is no tracked for rentings.'))
            else:
                if line.resource_ids:
                    raise ValidationError(_('The Sale Item should not be linked to resources as the line is not a rental one.'))

    @api.constrains('rental_booking_ids')
    def _check_rental_booking_ids(self):
        for line in self:
            if line.is_rental and line.state in ['sent', 'sale', 'done']:
                if line.product_id.rental_tracking == 'use_resource':
                    if not line.rental_booking_ids:
                        raise ValidationError(_('The Sale Item should be linked to rental bookings, as the product tracked resources.'))
                    if len(line.resource_ids) != len(line.rental_booking_ids) or line.resource_ids != line.rental_booking_ids.mapped('resource_id'):
                        raise ValidationError(_('Each linked resources should have created a rental booking.'))
                if line.product_id.rental_tracking == 'no':
                    if line.resource_ids:
                        raise ValidationError(_('The Sale Item should not be linked to resources as the product is no tracked for rentings.'))
            else:
                if line.rental_booking_ids:
                    raise ValidationError(_('The Sale Item should not be linked to rental bookings as the line is not a rental one.'))

    @api.constrains('resource_ids', 'product_uom_qty')
    def _check_resource_qty(self):
        for line in self:
            if line.is_rental:
                if line.product_id.rental_tracking == 'use_resource':
                    if len(line.resource_ids) != line.product_uom_qty:
                        raise ValidationError("The Sale Item must have as much resources selected than rental quantity ordered.")

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        for line in lines:
            if not line.is_expense and line.is_rental and line.state == 'sale':
                line.sudo().with_company(self.company_id).with_context(
                    default_company_id=self.company_id.id,
                )._rental_booking_generation()
        return lines

    def unlink(self):
        bookings = self.sudo().mapped('rental_booking_ids').filtered(lambda b: b.state in ['draft', 'reserved', 'cancel'])
        result = super(SaleOrderLine, self).unlink()
        bookings.unlink()
        return result

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

    def get_sale_order_line_multiline_description_sale(self, product):
        """ Override to customize the sale line description with rental informations (like dates, proper description, ...) """
        if self.is_rental:
            name = product.display_name
            if product.description_rental:
                name += '\n' + product.description_rental
            name += self._get_sale_order_line_multiline_description_variants()
            # adds dates in description (in TZ and lang of partner)
            if self.rental_start_date and self.rental_stop_date:
                start_str = tools.format_datetime(self.env, self.rental_start_date, tz=self.order_partner_id.tz, lang_code=self.order_partner_id.lang)
                end_str = tools.format_datetime(self.env, self.rental_stop_date, tz=self.order_partner_id.tz, lang_code=self.order_partner_id.lang)
                name += '\n'
                name += _("Rental from %s to %s") % (start_str, end_str)
        else:
            name = super(SaleOrderLine, self).get_sale_order_line_multiline_description_sale(product)
        return name

    # ---------------------------------------------------------
    # Create rental stuff
    # ---------------------------------------------------------

    def _rental_booking_generation(self):
        rental_booking_value_list = []
        for line in self.filtered('is_rental'):
            if line.product_id.rental_tracking == 'use_resource':
                already_booked_resource_ids = line.mapped('rental_booking_ids.resource_id').ids
                for resource in line.resource_ids: # create booking for resource that has not yet a booking generated
                    if resource.id not in already_booked_resource_ids:
                        rental_booking_value_list.append(line._rental_booking_prepare_values(resource))
                    already_booked_resource_ids.append(resource.id)
        return self.env['rental.booking'].create(rental_booking_value_list)

    def _rental_booking_prepare_values(self, resource):
        paddings = self.product_id._get_rental_paddings_timedelta()
        return {
            'sale_line_id': self.id,
            'name': self.order_id.name,
            'resource_id': resource.id,
            'date_from': self.rental_start_date - paddings['before'],
            'date_to': self.rental_stop_date + paddings['after'],
            'sale_order_id': self.order_id.id,
            'partner_id': self.order_partner_id.id,
            'partner_shipping_id': self.order_id.partner_shipping_id.id,
            'user_id': resource.user_id.id or self.order_id.user_id.id,
            'state': 'draft' if self.state in ['draft', 'sent']  else 'reserved',
            'agreement_id': self.product_id.rental_agreement_id.id if self.product_id.rental_agreement_id else False,
        }

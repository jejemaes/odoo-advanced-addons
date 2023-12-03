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
        grouped_data = self.env['rental.booking'].sudo().read_group([('sale_order_id', 'in', self.ids)], ['sale_order_id'], ['sale_order_id'])
        mapped_data = {db['sale_order_id'][0]: db['sale_order_id_count'] for db in grouped_data}
        for order in self:
            order.rental_count = mapped_data.get(order.id, 0)

    @api.depends('order_line.is_rental')
    def _compute_rental_line_count(self):
        for order in self:
            order.rental_line_count = len(order.order_line.filtered(lambda l: l.is_rental))

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

    def action_draft(self):
        """ When resetting the SO, the draft and confirmed rental should be reset too """
        result = super(SaleOrder, self).action_draft()
        self.mapped('order_line').filtered(lambda l: l.is_rental).mapped('rental_booking_ids').sudo().filtered(lambda b: b.state != 'done').action_reset()
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
        rental_sale_lines.mapped('rental_booking_ids').sudo().filtered(lambda b: b.state == 'draft').action_confirm()
        return result

    def action_cancel(self):
        """ When cancelling the SO, all bookings should be cancelled too """
        result = super(SaleOrder, self).action_cancel()
        self.mapped('order_line').filtered(lambda l: l.is_rental).mapped('rental_booking_ids').sudo().action_cancel()
        return result

    def action_generate_rental_booking(self):
        self.mapped('order_line')._rental_booking_generation()
        return True


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rental_product_id = fields.Many2one(
        related='product_id', readonly=False,
        store=False,  # dummy field only for display because of domain on product_id. The onchange will set the real product bypassing the domain
        domain="[('can_be_rented', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")

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

    @api.depends('rental_start_date', 'rental_stop_date')
    def _compute_name(self):
        super()._compute_name()

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
        mapping = lines_by_rental._get_delivered_quantity_by_rental([('state', 'in', ['confirmed', 'done'])])
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

    @api.depends('is_rental')
    def _compute_pricelist_item_id(self):
        for line in self.filtered(lambda sol: sol.is_rental):
            if not line.product_id or line.display_type or not line.order_id.pricelist_id:
                line.pricelist_item_id = False
            else:
                line.pricelist_item_id = line.order_id.pricelist_id._get_product_rule(
                    line.product_id,
                    line.product_uom_qty or 1.0,
                    uom=line.product_uom,
                    date=line.order_id.date_order,
                    **self._rental_get_product_context(), # tell in kwargs that this is a rental, not a sale (dates might be null)
                )

        super(SaleOrderLine, self.filtered(lambda sol: not sol.is_rental))._compute_pricelist_item_id()

    @api.depends('is_rental', 'rental_start_date', 'rental_stop_date')
    def _compute_price_unit(self):
        for line in self.filtered(lambda sol: sol.is_rental):
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            if line.qty_invoiced > 0:
                continue
            if not line.product_uom or not line.product_id or not line.order_id.pricelist_id:
                line.price_unit = 0.0
            else:
                if not line.rental_start_date or not line.rental_stop_date:
                    line.price_unit = 0.0
                else:
                    price = line.with_company(line.company_id)._get_display_price()
                    line.price_unit = line.product_id.with_context(**self._rental_get_product_context())._get_tax_included_unit_price(
                        line.company_id,
                        line.order_id.currency_id,
                        line.order_id.date_order,
                        'sale',
                        fiscal_position=line.order_id.fiscal_position_id,
                        product_price_unit=price,
                        product_currency=line.currency_id
                        # TODO force UoM ?
                    )

        super(SaleOrderLine, self.filtered(lambda sol: not sol.is_rental))._compute_price_unit()

    # TODO do we want to force unit Uom when renting ? we did not that before
    # @api.depends('product_id', 'is_rental')
    # def _compute_product_uom(self):
    #     rental_sale_lines = self.filtered(lambda sol: sol.is_rental)
    #     other_sale_lines = self.filtered(lambda sol: not sol.is_rental)

    #     if rental_sale_lines:
    #         unit_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
    #         for line in rental_sale_lines:
    #             line.product_uom = unit_uom
    #     super(SaleOrderLine, other_sale_lines)._compute_product_uom()


    @api.depends('is_rental', 'product_rental_tracking', 'resource_ids')
    def _compute_product_uom_qty(self):
        rental_tracked_sale_lines = self.filtered(lambda sol: sol.product_rental_tracking == 'use_resource')
        other_sale_lines = self.filtered(lambda sol: sol.product_rental_tracking != 'use_resource')

        for line in rental_tracked_sale_lines:
            line.product_uom_qty = len(line.resource_ids)

        super(SaleOrderLine, other_sale_lines)._compute_product_uom_qty()

    @api.onchange('rental_product_id')
    def _onchange_rental_product_id(self):
        self.product_id = self.rental_product_id

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
            if not line.is_expense and line.is_rental and line.state == 'sale' and line.resource_ids:
                line.sudo().with_company(self.company_id).with_context(
                    default_company_id=self.company_id.id,
                )._rental_booking_generation()
        return lines

    def unlink(self):
        bookings = self.sudo().mapped('rental_booking_ids').filtered(lambda b: b.state in ['draft', 'cancel'])
        result = super(SaleOrderLine, self).unlink()
        bookings.unlink()
        return result

    # ---------------------------------------------------------
    # Sale Business Extension
    # ---------------------------------------------------------

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

    def _get_sale_order_line_multiline_description_sale(self):
        """ Override to customize the sale line description with rental informations (like dates, proper description, ...) """
        if self.is_rental:
            name = self.product_id.display_name
            if self.product_id.description_rental:
                name += '\n' + self.product_id.description_rental
            name += self._get_sale_order_line_multiline_description_variants()
            # adds dates in description (in TZ and lang of partner)
            if self.rental_start_date and self.rental_stop_date:
                start_str = tools.format_datetime(self.env, self.rental_start_date, tz=self.order_partner_id.tz, lang_code=self.order_partner_id.lang)
                end_str = tools.format_datetime(self.env, self.rental_stop_date, tz=self.order_partner_id.tz, lang_code=self.order_partner_id.lang)
                name += '\n'
                name += _("Rental from %s to %s") % (start_str, end_str)
        else:
            name = super(SaleOrderLine, self).get_sale_order_line_multiline_description_sale()
        return name

    def _get_product_price_context(self):
        """Gives the context for product price computation. Enrich the native context with rental data if needed.

        :return: additional context to consider extra prices and flag if the price should be a rental price or a sale price.
        :rtype: dict
        """
        result = super()._get_product_price_context()
        if self.is_rental:
            result.update(self._rental_get_product_context())
        return result

    def _rental_get_product_context(self):
        """ Product context for rental. Used to provide additionnal rental data to compute base price. """
        result = {}
        result['sale_is_rental'] = self.is_rental
        result['rental_start_dt'] = fields.Datetime.to_string(self.rental_start_date)
        result['rental_stop_dt'] = fields.Datetime.to_string(self.rental_stop_date)
        return result

    def _get_protected_fields(self):
        fields = super()._get_protected_fields()
        fields += ['is_rental', 'rental_start_date', 'rental_stop_date']
        return fields

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
            'name': "%s - %s" % (self.order_id.name, self.order_id.partner_id.commercial_partner_id.name),
            'resource_id': resource.id,
            'date_from': self.rental_start_date - paddings['before'],
            'date_to': self.rental_stop_date + paddings['after'],
            'sale_order_id': self.order_id.id,
            'partner_id': self.order_partner_id.id,
            'partner_shipping_id': self.order_id.partner_shipping_id.id,
            'user_id': resource.user_id.id or self.order_id.user_id.id,
            'state': 'draft' if self.state in ['draft', 'sent']  else 'confirmed',
            'agreement_id': self.product_id.rental_agreement_id.id if self.product_id.rental_agreement_id else False,
        }

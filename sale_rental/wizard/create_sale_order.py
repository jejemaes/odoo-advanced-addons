# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectCreateSalesOrder(models.TransientModel):
    _name = 'rental.create.sale.order'
    _description = "Create SO from Rental Booking"

    @api.model
    def default_get(self, fields):
        result = super(ProjectCreateSalesOrder, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'rental.booking':
            raise UserError(_("You can only apply this action from a rental booking."))

        active_id = self._context.get('active_id')
        if 'rental_booking_id' in fields and active_id:
            rental = self.env['rental.booking'].browse(active_id)

            if not rental.resource_id.product_id:
                raise UserError(_("You can not create a Sales Order, since your resource is not linked to a product."))

            result['rental_booking_id'] = rental.id
            result['partner_id'] = rental.partner_id.id
            result['partner_shipping_id'] = rental.partner_shipping_id.id

        return result

    rental_booking_id = fields.Many2one('rental.booking', "Rental", required=True)
    company_id = fields.Many2one(related='rental_booking_id.company_id')

    partner_id = fields.Many2one('res.partner', string="Customer", required=True, help="Customer of the sales order")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', domain="[('commercial_partner_id', '=', partner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="Delivery address for current booking.")
    commercial_partner_id = fields.Many2one(related='partner_id.commercial_partner_id')

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True)
    currency_id = fields.Many2one(related='pricelist_id.currency_id', depends=["pricelist_id"], store=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    auto_confirm = fields.Boolean("Auto Confirm Order", compute='_compute_auto_confirm', store=True, readonly=False)

    product_id = fields.Many2one('product.product', string="Product", required=True, related='rental_booking_id.resource_id.product_id')
    price_unit = fields.Float("Unit Price")
    discount = fields.Float("Discount")
    rental_pricing_explanation = fields.Text("Pricing explanation", compute='_compute_rental_price_details', compute_sudo=True, help="Helper text to understand rental price computation.")

    rental_start_date = fields.Datetime(related='rental_booking_id.date_from', readonly=True)
    rental_stop_date = fields.Datetime(related='rental_booking_id.date_to', readonly=True)

    @api.depends('rental_booking_id')
    def _compute_auto_confirm(self):
        for wizard in self:
            if wizard.rental_booking_id.state in ['reserved', 'picked_up', 'returned', 'done']:
                wizard.auto_confirm = True
            else:
                wizard.auto_confirm = False

    @api.depends('product_id', 'rental_start_date', 'rental_stop_date', 'pricelist_id')
    def _compute_rental_price_details(self):
        for wizard in self:
            if wizard.product_id and wizard.rental_start_date and wizard.rental_stop_date and wizard.pricelist_id:
                if wizard.rental_start_date <= wizard.rental_stop_date:
                    pricing_explanation = wizard.product_id.with_context(lang=self.partner_id.lang or 'en_US').get_rental_pricing_explanation(wizard.rental_start_date, wizard.rental_stop_date, currency_id=self.currency_id.id)[wizard.product_id.id]
                    wizard.rental_pricing_explanation = pricing_explanation
                else:
                    wizard.rental_pricing_explanation = False
            else:
                wizard.rental_pricing_explanation = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_shipping_id = self.partner_id.address_get(['delivery'])['delivery']
            self.pricelist_id = self.with_company(self.company_id).partner_id.property_product_pricelist

    @api.onchange('product_id', 'rental_start_date', 'rental_stop_date', 'pricelist_id')
    def _onchange_rent_price_and_discount(self):
        if self.product_id and self.rental_start_date and self.rental_stop_date and self.pricelist_id:
            if self.rental_start_date <= self.rental_stop_date:
                pricing_data = self.product_id.get_rental_price(self.rental_start_date, self.rental_stop_date, self.pricelist_id.id, quantity=1)
                self.price_unit = pricing_data[self.product_id.id]['price_list']
                self.discount = pricing_data[self.product_id.id]['discount']

    def action_create_sale_order(self):
        # creates sales order
        sale_order = self._create_sale_order()

        # adds SO line
        sol_values = {
            'order_id': sale_order.id,
            'is_rental': True,
            'product_id': self.product_id.id,
            'price_unit': self.price_unit,
            'product_uom_qty': 1.0,
            'product_uom': self.product_id.uom_id.id,
            'discount': self.discount,
            'rental_start_date': self.rental_start_date,
            'rental_stop_date': self.rental_stop_date,
        }
        if self.product_id.rental_tracking == 'use_resource':
            sol_values['resource_ids'] = [(6, 0, [self.rental_booking_id.resource_id.id])]

        sale_order_line = self.env['sale.order.line'].create(sol_values)
        sale_order_line._compute_tax_id()

        sale_order_line.write({
            'name': sale_order_line.get_sale_order_line_multiline_description_sale(self.product_id),
        })

        # link booking to SO
        self.rental_booking_id.write({'sale_line_id': sale_order_line.id})

        # confirm SO
        if self.auto_confirm:
            sale_order.action_confirm()

        # return the action
        view_form_id = self.env.ref('sale.view_order_form').id
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action.update({
            'views': [(view_form_id, 'form')],
            'view_mode': 'form',
            'name': sale_order.name,
            'res_id': sale_order.id,
        })
        return action

    def _create_sale_order(self):
        """ Private implementation of generating the sales order """
        sale_order = self.env['sale.order'].create({
            'pricelist_id': self.pricelist_id.id,
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'company_id': self.company_id.id,
        })
        sale_order.onchange_partner_shipping_id()  # set the fiscal position
        return sale_order

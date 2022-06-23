# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from odoo.osv import expression
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        is_rental = kwargs.get('is_rental')
        if line_id:
            so_line = self.env['sale.order.line'].sudo().browse(line_id)
            if so_line.is_rental:
                is_rental = True
                kwargs.update({
                    'rental_start_dt': fields.Datetime.to_string(so_line.rental_start_date),
                    'rental_end_dt': fields.Datetime.to_string(so_line.rental_stop_date),
                })

        if is_rental:  # rental case: rental dates are in kwargs
            return self._rental_cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)

        return super(SaleOrder, self)._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)

    def _rental_cart_update(self, product_id=None, rental_start_dt=None, rental_end_dt=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        # cast into correct types
        rental_start_dt = fields.Datetime.from_string(rental_start_dt)
        rental_end_dt = fields.Datetime.from_string(rental_end_dt)
        try:  # copy/paste of odoo 14
            if add_qty is not None:
                add_qty = float(add_qty)
        except ValueError:
            add_qty = 1
        try:  # copy/paste of odoo 14
            if set_qty is not None:
                set_qty = float(set_qty)
        except ValueError:
            set_qty = 0

        # check SO can be modified (copy/paste from odoo 14)
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sales order which is not in draft status.'))

        SaleOrderLineSudo = self.env['sale.order.line'].sudo()

        if line_id:  # update case
            so_line = SaleOrderLineSudo.browse(line_id)

            # compute new quantity
            quantity = 0
            if set_qty:  # set qty to zero is not allowed, while adding zero is done when confirming order
                quantity = set_qty
            elif add_qty is not None:
                quantity = so_line.product_uom_qty + (add_qty or 0)

            if quantity > 0.0:
                pricelist_context = dict(self._context)
                pricelist_context.update({
                    'partner_id': self.partner_id.id,
                    'lang': self.partner_id.lang or 'en_US',
                })
                product = so_line.product_id.with_context(pricelist_context).with_company(self.company_id.id)

                # replace the resources
                resource_ids = False
                if product.rental_tracking == 'use_resource':
                    resource_ids = product.product_tmpl_id._rental_get_available_resources(rental_start_dt, rental_end_dt, quantity).ids

                    # raise if not enough resources
                    if len(resource_ids) != quantity:
                        raise UserError(_("Resources are not available anymore for you. Please remove your order line and try to set up new rental."))

                price = product.get_rental_price(rental_start_dt, rental_end_dt, self.pricelist_id.id, quantity=quantity, uom_id=False, date=False)[product.id]['price_list']
                so_line.write({
                    'product_uom_qty': quantity,
                    'price_unit': price,
                    'resource_ids': [(6, 0, resource_ids)]
                })
            else:  # remove zero or negative lines
                linked_line = so_line.linked_line_id
                so_line.unlink()
                if linked_line:  # update description of the parent
                    linked_line.name = linked_line.with_context(lang=self.partner_id.lang or 'en_US').get_sale_order_line_multiline_description_sale(linked_line.product_id)
                so_line = None  # as line has been removed

        else:  # create a new line
            sol_values = self._rental_cart_update_new_line_prepare_values(product_id, rental_start_dt, rental_end_dt, add_qty or set_qty, **kwargs)
            so_line = SaleOrderLineSudo.create(sol_values)

            # update SO line description
            so_line.name = so_line.with_context(lang=self.partner_id.lang or 'en_US').get_sale_order_line_multiline_description_sale(so_line.product_id)

        # link a product to the sales order
        if so_line and kwargs.get('linked_line_id'):
            linked_so_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
            so_line.write({
                'linked_line_id': linked_so_line.id,
            })
            linked_so_line.name = linked_so_line.with_context(lang=self.partner_id.lang or 'en_US').get_sale_order_line_multiline_description_sale(linked_so_line.product_id)

        if not so_line:  # as line has been removed
            return {
                'line_id': False,
                'quantity': 0.0,
                'option_ids': [],
            }

        option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == so_line.id)
        return {
            'line_id': so_line.id,
            'quantity': so_line.product_uom_qty,
            'option_ids': list(set(option_lines.ids))
        }

    def _rental_cart_update_new_line_prepare_values(self, product_id, rental_start_dt, rental_end_dt, qty, **kwargs):
        pricelist_context = dict(self._context)
        pricelist_context.update({
            'partner_id': self.partner_id.id,
            'lang': self.partner_id.lang or 'en_US',
        })
        product = self.env['product.product'].with_context(pricelist_context).with_company(self.company_id.id).browse(product_id)

        # compute the resources
        resource_ids = False
        if product.rental_tracking == 'use_resource':
            resource_ids = product.product_tmpl_id._rental_get_available_resources(rental_start_dt, rental_end_dt, qty).ids

            # raise if not enough resources
            if len(resource_ids) != qty:
                raise UserError(_("Resources are not available anymore for you. Please remove your order line and try to set up new rental."))

        # compute price and discout according to the pricelist discount policy
        price_data = product.get_rental_price(rental_start_dt, rental_end_dt, self.pricelist_id.id, quantity=qty, uom_id=False, date=False)[product.id]
        return {
            'order_id': self.id,
            'product_id': product_id,
            'product_uom_qty': qty,
            'price_unit': price_data['price_list'],
            'discount': price_data['discount'],
            'product_uom': product.uom_id.id,
            'is_rental': True,
            'rental_start_date': rental_start_dt,
            'rental_stop_date': rental_end_dt,
            'resource_ids': [(6, 0, resource_ids)] if resource_ids else False,
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    website_rental_unit_price = fields.Float(compute='_compute_website_rental_unit_price')

    @api.depends('price_unit')
    @api.depends_context('uid')
    def _compute_website_rental_unit_price(self):
        tax_field = 'total_excluded' if self.user_has_groups('account.group_show_line_subtotals_tax_excluded') else 'total_included'
        for line in self:
            line.website_rental_unit_price = line.tax_id.compute_all(line.price_unit, line.currency_id, line.product_uom_qty, line.product_id, line.order_partner_id)[tax_field]

# -*- coding: utf-8 -*-

from itertools import groupby
from re import search
from functools import partial

from odoo import api, fields, models, SUPERUSER_ID
from odoo.osv import expression
from odoo.exceptions import UserError


class PosOrderPrint(models.Model):
    _name = 'pos.order.kitchen.status'
    _description = 'Order Kitchen Status'
    _table = 'pos_order_kitchen_status'

    kitchen_id = fields.Many2one('restaurant.kitchen', string="Kitchen", required=True)
    order_id = fields.Many2one('pos.order', string="PoS Order", required=True)
    print_count = fields.Integer("Print Counter", default=0)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    kitchen_order_details = fields.Html("Order Details", compute='_compute_kitchen_order_details')

    kitchen_status_ids = fields.One2many('pos.order.kitchen.status', 'order_id', string="Kitchen Status", depends=['kitchen_ids'])
    kitchen_ids = fields.Many2many('restaurant.kitchen', 'pos_order_kitchen_status', 'order_id', 'kitchen_id', string="Involved Kitchens", readonly=True, help="")
    print_count = fields.Integer("Print Counter", compute='_compute_print_count', inverse='_inverse_print_count', search='_search_print_count', store=False)
    print_url = fields.Char(compute='_compute_print_url')

    @api.depends('kitchen_status_ids.print_count')
    @api.depends_context('kitchen_id')
    def _compute_print_count(self):
        kitchen_id = self.env.context['kitchen_id']
        status_list = self.env['pos.order.kitchen.status'].search([('order_id', 'in', self.ids), ('kitchen_id', '=', kitchen_id)])
        status_map = {status.order_id.id: status.print_count for status in status_list}
        for order in self:
            order.print_count = status_map.get(order.id, 0)

    def _inverse_print_count(self):
        kitchen_id = self.env.context['kitchen_id']
        status_list = self.env['pos.order.kitchen.status'].search([('order_id', 'in', self.ids), ('kitchen_id', '=', kitchen_id)])
        status_map = {status.order_id.id: status for status in status_list}
        status_to_create = []
        for order in self:
            status = status_map.get(order.id)
            if status:
                status.print_count = order.print_count
            else:
                status_to_create.append({
                    'kitchen_id': kitchen_id,
                    'order_id': order.id,
                    'print_count': order.print_count
                })
        if status_to_create:
            self.env['pos.order.kitchen.status'].create(status_to_create)

    def _search_print_count(self, operator, value):
        kitchen_id = self.env.context['kitchen_id']

        if operator not in expression.TERM_OPERATORS:  # prevent sql injection
            raise UserError("Invalide operator.")

        query = """
            SELECT S.order_id
            FROM %s S
            WHERE kitchen_id = %%s AND print_count %s %%s
        """ % (self.env['pos.order.kitchen.status']._table, operator)

        return [('id', 'inselect', (query, (kitchen_id, value)))]

    @api.depends_context('kitchen_id')
    def _compute_print_url(self):
        for order in self:
            order.print_url = '/restaurant/%s/%s/reprint' % (self.env.context['kitchen_id'], order.id)

    @api.depends('lines')
    @api.depends_context('kitchen_id')
    def _compute_kitchen_order_details(self):
        kitchen = self.env['restaurant.kitchen'].browse(self.env.context['kitchen_id'])

        for order in self:
            lines = kitchen.get_order_line(order)
            order.kitchen_order_details = self.env["ir.ui.view"]._render_template('pos_restaurant_kitchen.pos_order_reprint_receipt_order_line', {'lines': lines})

    @api.model
    def create(self, values):
        order = super(PosOrder, self).create(values)

        if order.config_id.is_kitchen_preparation:
            # extract categories
            pos_categories = order.lines.mapped('product_id.pos_categ_id')
            # select kitchen from the config that are involved in at least one pos line
            kitchen_ids = set()
            for kitchen in order.config_id.kitchen_ids:
                if kitchen.order_line_mode == 'all':
                    kitchen_ids.add(kitchen.id)
                elif kitchen.order_line_mode == 'category':
                    if set(kitchen.pos_category_ids.ids) & set(pos_categories.ids):
                        kitchen_ids.add(kitchen.id)
            # create kitchen status here, in order to having the default value set (m2m model problem)
            if kitchen_ids:
                value_to_create = []
                for kitchen_id in kitchen_ids:
                    value_to_create.append({
                        'order_id': order.id,
                        'kitchen_id': kitchen_id,
                    })
                self.env['pos.order.kitchen.status'].sudo().create(value_to_create)

        return order

    def action_mark_as_print(self):
        self.sudo().write({'print_count': -1})
        return True

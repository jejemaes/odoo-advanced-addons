# -*- coding: utf-8 -*-

from itertools import groupby
from re import search
from functools import partial

from odoo import api, fields, models, SUPERUSER_ID
from odoo.osv import expression


class PosOrder(models.Model):
    _inherit = 'pos.order'

    print_count = fields.Integer("Print Counter", default=0)
    print_url = fields.Char(compute='_compute_print_url')
    kitchen_ids = fields.Many2many('restaurant.kitchen', 'pos_order_kitchen_rel', 'order_id', 'kitchen_id', string="Kitchens", readonly=True)
    kitchen_order_details = fields.Html("Order Details", compute='_compute_kitchen_order_details')

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
    def _complete_values_from_session(self, session, values):
        values = super()._complete_values_from_session(session, values)

        if session.config_id.is_kitchen_preparation:
            kitchen_ids = session.config_id.kitchen_ids.filtered(lambda k: k.order_line_mode == 'all').ids
            if kitchen_ids:
                values['kitchen_ids'] = [(6, 0, kitchen_ids)]

        return values


# class PosOrderLine(models.Model):
#     _inherit = 'pos.order.line'

#     @api.model
#     def _default_kitchen_stage_id(self):
#         return self.env['restaurant.kitchen.stage'].search([], limit=1)

#     order_id = fields.Many2one(readonly=True)
#     config_id = fields.Many2one('pos.config', string="Point of Sale", related='order_id.config_id')
#     table_id = fields.Many2one('restaurant.table', related='order_id.table_id')
#     user_id = fields.Many2one('res.users', string="User", related='order_id.user_id')

#     kitchen_ids = fields.Many2many('restaurant.kitchen', 'pos_order_line_kitchen_rel', 'order_line_id', 'kitchen_id', string="Kitchens", readonly=True)
#     kitchen_stage_id = fields.Many2one(
#         'restaurant.kitchen.stage', string='Preparation Stage', index=True, default=_default_kitchen_stage_id,
#         copy=False, group_expand='_read_group_stage_ids', ondelete='set null')
#     kitchen_stage_closed = fields.Boolean(related='kitchen_stage_id.is_closed', search='_search_kitchen_stage_closed')
#     kitchen_stage_color = fields.Integer(related='kitchen_stage_id.color')
#     kitchen_stage_button_text = fields.Char(related='kitchen_stage_id.button_text')

#     @api.model
#     def _read_group_stage_ids(self, stages, domain, order):
#         stage_ids = stages._search([], order=order)
#         return stages.browse(stage_ids)

#     def _search_kitchen_stage_closed(self, operator, value):
#         closed_stages = self.env['restaurant.kitchen.stage'].search([('is_closed', '=', True)])
#         if operator in expression.NEGATIVE_TERM_OPERATORS:
#             new_operator = 'not in' if value else 'in'
#         else:
#             new_operator = 'in' if value else 'not in'
#         return [('kitchen_stage_id', new_operator, closed_stages.ids)]

#     def _order_line_fields(self, line, session_id=None):
#         """ Hook to add preparation IDs, for the line to be visible in the preparation. """
#         line = super(PosOrderLine, self)._order_line_fields(line, session_id=session_id)
#         if session_id:
#             session = self.env['pos.session'].browse(session_id).exists() if session_id else None
#             if session and session.config_id.kitchen_ids:
#                 product = self.env['product.product'].browse(line[2]['product_id'])
#                 kitchen_ids = [kitchen.id for kitchen in session.config_id.kitchen_ids if product.pos_categ_id in kitchen.pos_category_ids]
#                 line[2]['kitchen_ids'] = [(6, 0, kitchen_ids)]
#         return line

#     def action_next_stage(self):
#         if self.kitchen_stage_id:
#             kitchen_stage = self.env['restaurant.kitchen.stage'].search([('sequence', '>', self.kitchen_stage_id.sequence)], limit=1)
#             self.write({'kitchen_stage_id': kitchen_stage.id})

#     def action_reset(self):
#         kitchen_stage = self.env['restaurant.kitchen.stage'].search([], limit=1)
#         self.write({'kitchen_stage_id': kitchen_stage.id})

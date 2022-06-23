# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class RestaurantKitchen(models.Model):
    _name = 'restaurant.kitchen'
    _description = 'Restaurant Kitchen'

    name = fields.Char('Kitchen Name', required=True)
    order_line_mode = fields.Selection([
        ('all', 'All Lines of the orders'),
        ('category', 'Select PoS Categories'),
    ], required=True, default='all')
    refresh_timer = fields.Integer("Dashboard Refresh Timer", default=10000, help="Refreshing period for dashboard in milis.")
    pos_category_ids = fields.Many2many('pos.category', 'restaurant_kitchen_pos_category_rel', 'kitchen_id', 'category_id')
    company_id = fields.Many2one('res.company', string="Company", required=True, index=True, default=lambda self: self.env.company.id)

    def action_mark_all_as_print(self):
        self.env['pos.order.kitchen.status'].sudo().search([('kitchen_id', 'in', self.ids), ('print_count', '=', 0)]).write({'print_count': -1})
        return True

    def action_order_dashbaord(self):
        action = self.env.ref('pos_restaurant_kitchen.pos_order_action').sudo().read()[0]
        # get evaluated context as dict
        context = {}
        if action.get('context'):
            eval_context = self.env['ir.actions.actions']._get_eval_context()
            if not self._context.get('active_id'):
                eval_context.update({'active_id': self.id})
            context = safe_eval(action['context'], eval_context)
        # set refresh timer if needed
        if self.refresh_timer:
            context['kanban_autorefresh'] = self.refresh_timer
        action['context'] = context

        # name of dashboard
        action['name'] = self.name
        action['display_name'] = self.name
        return action

    def get_order_line(self, order):
        if self.order_line_mode == 'all':
            return order.lines

        if self.order_line_mode == 'category':
            return order.lines.filtered(lambda line: line.product_id.pos_categ_id in self.pos_category_ids)

        return self.env['pos.order.line']

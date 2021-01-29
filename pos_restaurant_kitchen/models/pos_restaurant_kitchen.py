# -*- coding: utf-8 -*-

from odoo import fields, models


class RestaurantKitchen(models.Model):
    _name = 'restaurant.kitchen'
    _description = 'Restaurant Kitchen'

    name = fields.Char('Kitchen Name', required=True, default='Kitchen')
    pos_category_ids = fields.Many2many('pos.category', 'restaurant_kitchen_pos_category_rel', 'kitchen_id', 'category_id')
    company_id = fields.Many2one('res.company', string="Company", required=True, index=True, default=lambda self: self.env.company.id)

    def action_mark_all_as_done(self):
        final_stage = self.env['restaurant.kitchen.stage'].search([('is_closed', '=', True)], limit=1)
        order_lines = self.env['pos.order.line'].search([('kitchen_stage_id', '!=', final_stage.id), ('kitchen_ids', 'in', self.ids)])
        order_lines.write({'kitchen_stage_id': final_stage.id})


class RestaurantKitchenStage(models.Model):
    _name = 'restaurant.kitchen.stage'
    _description = "Kitchen Preparation Stage"
    _rec_name = 'name'
    _order = "sequence, name, id"

    name = fields.Char('Stage Name', required=True)
    button_text = fields.Char("Button Text", default='Next Step')
    sequence = fields.Integer('Sequence', default=5, help="Used to order stages. Lower is better.")
    color = fields.Integer('Color', default=1)
    is_closed = fields.Boolean('Is Final Stage')
    fold = fields.Boolean('Folded in Pipeline', help="This stage is folded in the kanban view when there are no records in that stage to display.")
    company_id = fields.Many2one('res.company', string="Company", required=True, index=True, default=lambda self: self.env.company.id)

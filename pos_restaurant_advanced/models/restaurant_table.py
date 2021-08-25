# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class RestaurantFloor(models.Model):

    _inherit = 'restaurant.floor'

    def action_copy_with_table(self):
        for floor in self:
            new_floor = floor.copy()
            for table in self.env['restaurant.table'].search([('floor_id', '=', floor.id)]):
                table.copy({'floor_id': new_floor.id})

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _("%s (copy)", self.name)
        return super(RestaurantFloor, self).copy(default)

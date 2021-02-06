# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

WIDTH = 250
HEIGHT = 100
MARGIN = 10
COL_SIZE = 5


class RestaurantTableGenerator(models.TransientModel):

    _name = 'restaurant.table.generator'
    _description = "Restaurant Table Generator"

    @api.model
    def default_get(self, fields_list=None):
        result = super(RestaurantTableGenerator, self).default_get(fields_list=fields_list)

        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        active_id = self._context.get('active_id')

        if active_model == 'restaurant.floor':
            if active_ids:
                result['floor_ids'] = [(6, 0, active_ids)]
            elif active_id:
                result['floor_ids'] = [(6, 0, [active_id])]

        return result

    floor_ids = fields.Many2many('restaurant.floor', 'restaurant_table_generator__floor_rel', 'wizard_id', 'floor_id', string="Floors")

    number_start = fields.Integer("Start Number", default=1, required=True)
    number_end = fields.Integer("End Number", default=10, required=True)
    shape = fields.Selection([('square', 'Square'), ('round', 'Round')], string='Shape', required=True, default='square')
    seats = fields.Integer('Seats', default=1, help="The default number of customer served at this table.")
    color = fields.Char('Color', help="The table's color, expressed as a valid 'background' CSS property value")

    def action_generate(self):
        for floor in self.floor_ids:
            self._generate_table(floor)

    def _generate_table(self, floor):
        table_value_list = []
        col = 0
        for index, num in enumerate(range(self.number_start, self.number_end + 1)):
            row_index = index % COL_SIZE
            if row_index == 0:
                col += 1

            table_values = self._get_table_values(num, floor, index)
            table_values['position_v'] = row_index * (MARGIN + HEIGHT)
            table_values['position_h'] = col * (MARGIN + WIDTH)
            table_value_list.append(table_values)

        self.env['restaurant.table'].create(table_value_list)

    def _get_table_values(self, num, floor, position):
        return {
            'name': _("Table %s") % (str(num),),
            'floor_id': floor.id,
            'width': WIDTH,
            'height': HEIGHT,
            'seats': self.seats,
            'color': self.color,
        }

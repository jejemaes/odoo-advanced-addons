# -*- coding: utf-8 -*-

from odoo import api, fields, models


class RestaurantMenuPrintQRCode(models.TransientModel):

    _name = 'restaurant.menu.print.qrcode'
    _description = "Print Restaurant Menu QRCode Badge"

    @api.model
    def default_get(self, fields_list=None):
        result = super(RestaurantMenuPrintQRCode, self).default_get(fields_list=fields_list)

        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids')
        active_id = self._context.get('active_id')

        if active_model == 'restaurant.table' and active_ids:
            result['table_ids'] = [(6, 0, active_ids)]
        if active_model == 'restaurant.menu' and active_id:
            result['menu_id'] = active_id

        return result

    menu_id = fields.Many2one('restaurant.menu', string='Menu', required=True)
    table_select_mode = fields.Selection([
        ('by_table', 'Select Table'),
        ('by_floor', 'Select Floor'),
    ], string="Table Selection Mode", default='by_floor', required=True)
    table_ids = fields.Many2many('restaurant.table', 'restaurant_menu_print_qrcode_table_rel', 'wizard_id', 'table_id', string="Tables")
    floor_ids = fields.Many2many('restaurant.floor', 'restaurant_menu_print_qrcode_floor_rel', 'wizard_id', 'floor_id', string="Floors")
    include_seats = fields.Boolean("Show Max Seats", default=True, help="Show max people allowed around the table, on the QRCode badge")

    def print_report(self):
        datas = {
            'restaurant_menu_id': self.menu_id.id,
            'include_seats': self.include_seats,
        }
        tables = self._get_tables()
        return self.env.ref('pos_restaurant_menu.restaurant_table_action_report_qrcode').report_action(tables, data=datas, config=False)

    def _get_tables(self):
        tables = self.table_ids
        if self.table_select_mode == 'by_floor':
            tables = self.env['restaurant.table'].search([('floor_id', 'in', self.floor_ids.ids)])
        return tables

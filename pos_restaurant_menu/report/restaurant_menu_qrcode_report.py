# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ReportRestaurantMenuQRCode(models.AbstractModel):
    _name = 'report.pos_restaurant_menu.pos_restaurant_menu_qrcode'
    _description = "Restaurant Menu QRCode"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}

        restaurant_menu = self.env['restaurant.menu'].browse(data['restaurant_menu_id'])

        docids = data['context'].get('active_ids', [])
        docs = self.env['restaurant.table'].browse(docids)

        data.update({
            'doc_ids': docids,
            'doc_model': 'restaurant.table',
            'docs': docs,
            'restaurant_menu': restaurant_menu,
        })

        return data

# -*- coding: utf-8 -*-

import io
import base64
import qrcode

from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slug


class RestaurantMenun(models.Model):
    _name = 'restaurant.menu'
    _description = 'Restaurant Menu'
    _rec_name = 'name'

    name = fields.Char('Name', required=True, copy=False)
    pos_category_ids = fields.Many2many('pos.category', 'restaurant_menu_product_category_rel', 'menu_id', 'category_id')
    is_published = fields.Boolean("Is Publisehd", default=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, index=True, default=lambda self: self.env.company.id)

    url = fields.Char("Url", compute='_compute_url')
    qrcode = fields.Binary("QR Code", compute='_compute_qrcode', attachment=False, store=False, readonly=True)
    badge_extra_content = fields.Html("QR Code badge extra content", help="Footer on QRCode badges for tables")

    _sql_constraints = [
        ('unique_name_per_company', 'UNIQUE(company_id, name)', 'That name is already taken.'),
    ]

    @api.depends('name', 'company_id')
    def _compute_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for menu in self:
            if menu.id:
                if menu.name:
                    menu.url = '%s/restaurant/%s' % (base_url, slug(menu),)
                else:
                    menu.url = False
            else:
                menu.url = False

    @api.depends('url')
    def _compute_qrcode(self):
        for menu in self:
            url = menu.url
            if url:
                data = io.BytesIO()
                qrcode.make(url.encode(), box_size=12, version=3).save(data, optimise=True, format='PNG')
                menu.qrcode = base64.b64encode(data.getvalue()).decode()
            else:
                menu.qrcode = False

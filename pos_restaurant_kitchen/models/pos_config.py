# -*- coding: utf-8 -*-

from odoo import fields, models


class Posconfig(models.Model):
    _inherit = 'pos.config'

    is_kitchen_preparation = fields.Boolean("Preparation in Kitchens")
    kitchen_ids = fields.Many2many('restaurant.kitchen', 'pos_config_kitchen_rel', 'config_id', 'kitchen_id', string="Kitchens")

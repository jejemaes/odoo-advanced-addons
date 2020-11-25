# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_rental_padding_before = fields.Float("Before Security Time", default_model='product.template')
    default_rental_padding_after = fields.Float("After Security Time", default_model='product.template')

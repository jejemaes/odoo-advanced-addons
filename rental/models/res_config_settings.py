# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rental_agreement_id = fields.Many2one('rental.agreement', "Rental Agreement", related='company_id.rental_agreement_id', readonly=False)

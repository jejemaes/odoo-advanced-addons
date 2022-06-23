# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    rental_agreement_id = fields.Many2one('rental.agreement', "Rental Agreement")

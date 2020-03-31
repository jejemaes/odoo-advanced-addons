# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AbstractRentalTenure(models.AbstractModel):
    _inherit = 'rental.tenure.abstract'

    website_rent_price = fields.Float("Public Price", compute='_compute_website_rental_price')

    def _compute_website_rental_price(self):
        for tenure in self:
            tenure.website_rent_price = tenure.rent_price

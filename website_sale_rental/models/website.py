# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.osv import expression


class Website(models.Model):
    _inherit = "website"

    def _product_domain(self):
        domain = super()._product_domain()
        return expression.OR([domain, [("can_be_rented", "=", True)]])

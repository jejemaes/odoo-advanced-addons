# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.osv import expression


class Website(models.Model):
    _inherit = "website"

    def sale_product_domain(self):
        domain = super(Website, self).sale_product_domain()  # [('sale_ok', '=', True), ('website_id', 'in', (False, 1))]
        domain = ['&', '|'] + [("can_be_rented", "=", True)] + domain  # normalize the domain in order to
        return domain

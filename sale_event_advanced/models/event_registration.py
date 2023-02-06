# -*- coding: utf-8 -*-

from odoo import api, fields, models


class EventRegistration(models.Model):
    _inherit = "event.registration"

    def _synchronize_so_line_values(self, so_line):
        res = super()._synchronize_so_line_values(so_line)
        if so_line and so_line.event_id.registration_multi_qty:
            res.update({"qty": int(so_line.product_uom_qty)})
        return res

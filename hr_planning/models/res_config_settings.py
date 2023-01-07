# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    planning_allow_self_assign = fields.Boolean("Allow Assignment", default=False, readonly=False,
        related="company_id.planning_allow_self_assign", help="Let your employees assign themselves from shifts")
    planning_allow_self_unassign = fields.Boolean("Allow Unassignment", default=False, readonly=False,
        related="company_id.planning_allow_self_unassign", help="Let your employees un-assign themselves from shifts when unavailable")

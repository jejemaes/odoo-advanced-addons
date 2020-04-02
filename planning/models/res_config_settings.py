# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    planning_allow_self_assign = fields.Boolean("Allow Assignment", default=False, readonly=False,
        related="company_id.planning_allow_self_assign", help="Let your employees assign themselves from shifts")
    planning_allow_self_unassign = fields.Boolean("Allow Unassignment", default=False, readonly=False,
        related="company_id.planning_allow_self_unassign", help="Let your employees un-assign themselves from shifts when unavailable")

    planning_default_shift_duration = fields.Integer(related='company_id.planning_default_shift_duration', readonly=False)
    planning_default_shift_uom = fields.Selection(related='company_id.planning_default_shift_uom', readonly=False)

    planning_default_planning_duration = fields.Integer(related='company_id.planning_default_planning_duration', readonly=False)
    planning_default_planning_uom = fields.Selection(related='company_id.planning_default_planning_uom', readonly=False)

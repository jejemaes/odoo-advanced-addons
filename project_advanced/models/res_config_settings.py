# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_project_template = fields.Boolean("Use Project Template", implied_group='project_advanced.group_project_template', group="project.group_project_user")
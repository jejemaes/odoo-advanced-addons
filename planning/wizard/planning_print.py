# -*- coding: utf-8 -*-
import time

from odoo import api, fields, models


class PlanningPrintWizard(models.TransientModel):

    _name = 'planning.print'
    _description = "Planning Print Wizard"

    @api.model
    def default_get(self, fields):
        result = super(PlanningPrintWizard, self).default_get(fields)

        if self.env.context.get('active_model') == 'planning.planning':
            result['planning_id'] = self.env.context.get('active_id')
        return result

    planning_id = fields.Many2one('planning.planning', string='Planning', required=True)
    display_scale = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month')
    ], string='Scale per page', required=True, default='day')
    group_by_mode = fields.Selection([
        ('role', 'By Role'),
        ('employee', 'By Employee'),
    ], string='Group shifts', required=True, default='role')

    def action_print(self):
        self.ensure_one()

        shifts = self.env['planning.shift'].search(self.planning_id.get_shift_domain())
        data = {
            'docs': shifts,
            'doc_ids': shifts.ids,
            'scale': self.display_scale,
            'report_title': self.planning_id.name,
            'group_by_mode': self.group_by_mode,
        }
        return self.env.ref('planning.planning_shift_action_report').report_action(shifts.ids, data=data)

# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class PlanningSend(models.TransientModel):
    _name = 'planning.send'
    _description = "Send Planning"

    @api.model
    def default_get(self, fields):
        result = super(PlanningSend, self).default_get(fields)

        if self.env.context.get('active_model') == 'planning.planning':
            result['planning_id'] = self.env.context.get('active_id')
        return result

    planning_id = fields.Many2one('planning.planning', required=True)
    start_datetime = fields.Datetime(related='planning_id.date_start', string="Period")
    end_datetime = fields.Datetime(related='planning_id.date_start')
    shift_ids = fields.Many2many('planning.shift', compute='_compute_shift_ids')

    note = fields.Text("Extra Message", help="Additional message displayed in the email sent to employees")
    recipient_mode = fields.Selection([('by_employee', 'Employee'), ('by_department', 'Department')], required=True, string="Mode", default='by_employee')
    department_id = fields.Many2one('hr.department', string="Department")
    employee_ids = fields.Many2many('hr.employee', string="Employees", help="Employees who will receive planning by email if you click on publish & send.")

    @api.depends('planning_id')
    def _compute_shift_ids(self):
        for wiz in self:
            if wiz.planning_id:
                wiz.shift_ids = self.env['planning.shift'].search(wiz.planning_id.get_shift_domain())
            else:
                wiz.shift_ids = False

    @api.onchange('planning_id', 'recipient_mode')
    def _onchange_employee_ids(self):
        if self.recipient_mode == 'by_employee':
            self.employee_ids = self.shift_ids.mapped('employee_id')
        else:
            self.employee_ids = False

    def _get_employees_to_send(self):
        if self.recipient_mode == 'by_employee':
            return self.employee_ids
        return self.env['hr.employee'].search([('department_id', '=', self.department_id.id)])

    def action_send_and_publish(self):
        self.action_publish()
        employees_to_send = self._get_employees_to_send()
        return self.planning_id._send_planning(message=self.note, employees=employees_to_send)

    def action_publish(self):
        self.shift_ids.action_mark_as_published()
        return True

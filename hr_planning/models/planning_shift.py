# -*- coding: utf-8 -*-

from collections import namedtuple
from datetime import date, datetime, timedelta
import pytz
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import date_utils
from odoo.addons.resource.models.resource import float_to_time


ShiftSlice = namedtuple('ShiftSlice', ['start', 'stop', 'label', 'shift'])


class PlanningShift(models.Model):
    _inherit = 'planning.shift'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True, compute_sudo=True)

    # publishing
    publication_date = fields.Datetime("Last Sent Date", copy=False, help="Last date when the shift was published on employee's plannings.")
    #publication_warning = fields.Boolean("Publication Warning")

    # tools
    is_my_shift = fields.Boolean(compute='_compute_is_my_shift', search='_search_is_my_shift')
    can_self_assign = fields.Boolean("Can assign himself", compute='_compute_can_self_assign')
    can_self_unassign = fields.Boolean("Can unassign himself", compute='_compute_can_self_unassign')

    @api.depends('employee_id')
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.employee_id.department_id

    @api.depends('employee_id')
    def _compute_is_my_shift(self):
        for shift in self:
            shift.is_my_shift = bool(shift.employee_id in self.env.user.employee_ids)

    def _search_is_my_shift(self, operator, value):
        new_operator = 'in'
        if (operator in expression.NEGATIVE_TERM_OPERATORS and value) or (operator not in expression.NEGATIVE_TERM_OPERATORS and not value):
            new_operator = 'not in'
        return [('employee_id', new_operator, self.env.user.employee_ids.ids)]

    @api.depends('company_id', 'employee_id')
    def _compute_can_self_assign(self):
        for shift in self:
            shift.can_self_assign = shift.company_id.planning_allow_self_assign and not shift.employee_id

    @api.depends('company_id', 'employee_id')
    def _compute_can_self_unassign(self):
        for shift in self:
            shift.can_self_unassign = shift.company_id.planning_allow_self_assign and shift.employee_id in self.env.user.employee_ids

    # ----------------------------------------------------------------------------
    # ORM Overrides
    # ----------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, value_list):
        # employee forces resource
        employee_ids = [vals['employee_id'] for vals in value_list if vals.get('employee_id')]
        employees = self.env['hr.employee'].browse(employee_ids)
        employee_resource_map = {employee.id: employee.resource_id.id for employee in employees}

        for vals in value_list:
            if vals.get('employee_id'):
                vals['resource_id'] = employee_resource_map[vals['employee_id']]

        return super(PlanningShift, self).create(value_list)

    def write(self, values):
        if 'employee_id' in values:
            employee_id = values['employee_id']
            resource_id = False
            if employee_id:
                resource_id = self.env['hr.employee'].browse(employee_id).resource_id.id
            values['resource_id'] = resource_id
        return super(PlanningShift, self).write(values)

    # ----------------------------------------------------------------------------
    # Actions Methods
    # ----------------------------------------------------------------------------

    def action_self_assign(self):
        if self.can_self_assign:
            self.sudo().write({'employee_id': self.env.user.employee_id.id})
            return True
        return False

    def action_self_unassign(self):
        if self.can_unself_assign:
            self.sudo().write({'employee_id': False})
            return True
        return False

    def action_mark_as_published(self):
        self.write({
            'publication_date': fields.Datetime.now()
        })
        return True

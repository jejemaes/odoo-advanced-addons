# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class PlanningShift(models.Model):
    _name = 'planning.shift'
    _description = 'Planning Shift'
    _order = 'date_from desc'
    _inherits = {'resource.calendar.leaves':'resource_time_id'}

    resource_time_id = fields.Many2one('resource.calendar.leaves', string="Time Entry", required=True, domain=[('time_type', '=', 'planning')], auto_join=True, ondelete='cascade')
    time_type = fields.Selection(related='resource_time_id.time_type', inherited=True, default='planning')
    date_from = fields.Datetime(inherited=True, related='resource_time_id.date_from')
    date_to = fields.Datetime(inherited=True, related='resource_time_id.date_from')
    name = fields.Char("Name", required=True, inherited=True)

    role_id = fields.Many2one('planning.role', string="Role", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True, compute_sudo=True)

    note = fields.Text("Note")
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.user.company_id)
    overlap_count = fields.Integer("Number of shift overlapping", compute='_compute_overlap_count')

    # publication
    publication_date = fields.Datetime("Last Publication Date")
    publication_warning = fields.Boolean("Publication Warning")

    # tools
    is_my_shift = fields.Boolean(compute='_compute_is_my_shift', search='_search_is_my_shift')
    can_self_assign = fields.Boolean("Can assign himself", compute='_compute_can_self_assign')
    can_self_unassign = fields.Boolean("Can assign himself", compute='_compute_can_self_unassign')

    @api.depends('employee_id')
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.employee_id.department_id

    @api.depends('date_from', 'date_to')
    def _compute_overlap_count(self):
        overlap_count_map = {}
        if self.ids:
            query = """
                SELECT t.time_id AS time_id, COUNT(t.time_overlap_id) AS overlap_count
                FROM (
                    SELECT R1.id AS time_id, R2.id AS time_overlap_id
                    FROM resource_calendar_leaves R1
                        INNER JOIN resource_calendar_leaves R2 ON (R1.date_to > R2.date_from AND R1.date_from < R2.date_to AND R1.id != R2.id)
                    WHERE R1.time_type = 'planning'
                        AND R2.time_type = 'planning'
                        AND R1.resource_id = R2.resource_id
                        AND R1.id IN %s
                ) AS t
                GROUP BY t.time_id
            """
            self.env.cr.execute(query, (tuple(self.mapped('resource_time_id').ids),))
            data = self.env.cr.dictfetchall()
            overlap_count_map = {item['time_id']: item['overlap_count'] for item in data}

        for shift in self:
            shift.overlap_count = overlap_count_map.get(shift.resource_time_id.id, 0)

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

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from and not self.date_to:
            date_from = fields.Datetime.from_string(self.date_from)
            self.date_to = date_from + self.company_id.planning_get_default_shift_timedelta()

    @api.onchange('role_id')
    def _onchange_role_id(self):
        if not self.note:
            self.note = self.role_id.description

    # ----------------------------------------------------------------------------
    # ORM Overrides
    # ----------------------------------------------------------------------------

    def name_get(self):
        group_by_fields = self.env.context.get('group_by', [])

        result = []
        for shift in self:
            name_get_fields = shift._name_get_fields()
            name_parts = []
            for fname in name_get_fields:
                if fname not in group_by_fields and shift[fname]:
                    if self._fields[fname].type == 'many2one':
                        name_parts.append(shift[fname].display_name)
                    else:
                        name_parts.append(str(shift[fname]))
            result.append((shift.id, _(' - ').join(name_parts)))
        return result

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

    def action_view_overlap(self):
        query = """
            SELECT R2.id AS time_id
            FROM resource_calendar_leaves R1
                INNER JOIN resource_calendar_leaves R2 ON (R1.date_to > R2.date_from AND R1.date_from < R2.date_to)
            WHERE R1.time_type = 'planning'
                AND R2.time_type = 'planning'
                AND R1.resource_id = R2.resource_id
                AND R1.id IN %s
        """
        self.env.cr.execute(query, (tuple(self.mapped('resource_time_id').ids),))
        resource_time_ids = [item['time_id'] for item in self.env.cr.dictfetchall()]
        domain = [('resource_time_id', 'in', resource_time_ids)]

        action = self.env.ref('planning.planning_shift_action_schedule').read()[0]
        action['domain'] = domain
        return action

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

    # ----------------------------------------------------------------------------
    # Business Methods
    # ----------------------------------------------------------------------------

    def _name_get_fields(self):
        self.ensure_one()
        return ['id', 'employee_id', 'role_id', 'name']

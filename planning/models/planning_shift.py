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


class Role(models.Model):
    _name = 'planning.role'
    _description = 'Planning Role'
    _order = 'name desc'

    name = fields.Char("Title", required=True)
    color = fields.Integer("Color", default=0)
    description = fields.Char("Description")


class PlanningShift(models.Model):
    _name = 'planning.shift'
    _description = 'Planning Shift'
    _order = 'date_from desc'
    _inherits = {'resource.calendar.leaves':'resource_time_id'}

    resource_time_id = fields.Many2one('resource.calendar.leaves', string="Time Entry", required=True, domain=[('time_type', '=', 'planning')], auto_join=True, ondelete='cascade')
    time_type = fields.Selection(related='resource_time_id.time_type', inherited=True, default='planning')
    date_from = fields.Datetime(inherited=True, related='resource_time_id.date_from')
    date_to = fields.Datetime(inherited=True, related='resource_time_id.date_from')
    name = fields.Char("Internal Name", inherited=True)

    role_id = fields.Many2one('planning.role', string="Role", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', "Department", compute='_compute_department_id', store=True, compute_sudo=True)
    user_id = fields.Many2one('res.users', string="User", related='employee_id.user_id', store=True, readonly=True)

    note = fields.Text("Note", help="Public shift description. Will be displayed on planning web page.")
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.user.company_id)
    overlap_count = fields.Integer("Number of shift overlapping", compute='_compute_overlap_count')

    # publishing
    publication_date = fields.Datetime("Last Sent Date", copy=False, help="Last date when the shift was published on employee's plannings.")
    #publication_warning = fields.Boolean("Publication Warning")

    # template
    template_autocomplete_ids = fields.Many2many('planning.shift.template', store=False, compute='_compute_template_autocomplete_ids')
    template_id = fields.Many2one('planning.shift.template', string='Shift Templates')

    # tools
    is_my_shift = fields.Boolean(compute='_compute_is_my_shift', search='_search_is_my_shift')
    can_self_assign = fields.Boolean("Can assign himself", compute='_compute_can_self_assign')
    can_self_unassign = fields.Boolean("Can unassign himself", compute='_compute_can_self_unassign')

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

    @api.depends('role_id', 'employee_id')
    def _compute_template_autocomplete_ids(self):
        domain = self._get_domain_template_slots()
        templates = self.env['planning.shift.template'].search(domain, order='start_time', limit=10)
        self.template_autocomplete_ids = templates + self.template_id

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

    @api.onchange('date_from', 'date_to')
    def _onchange_reset_tempalte(self):
        if self.date_from and self.date_to:
            self.template_id = False

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from and not self.date_to:
            date_from = fields.Datetime.from_string(self.date_from)
            self.date_to = date_from + self.company_id.planning_get_default_shift_timedelta()

    @api.onchange('role_id')
    def _onchange_role_id(self):
        if not self.note:
            self.note = self.role_id.description

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.role_id = self.template_id.role_id

            if self.date_from:
                date_from = fields.Datetime.from_string(self.date_from)
                # template is applied in user TZ. Setting '9am' as start date is not simply replace
                # the hours part of the date_from. We need to handle the user timezone in the
                # computation.
                local_tz = pytz.timezone(self._context.get('tz', 'UTC'))
                tz_offset = -int(date_from.astimezone(local_tz).utcoffset().total_seconds()/60)

                start_time = float_to_time(self.template_id.start_time)
                date_from = date_from.replace(hour=start_time.hour, minute=start_time.minute)
                self.date_from = date_from + timedelta(minutes=tz_offset)

                duration = float_to_time(self.template_id.duration)
                self.date_to = self.date_from + timedelta(hours=duration.hour, minutes=duration.minute)
        else:
            self.role_id = None

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

    def action_mark_as_published(self):
        self.write({
            'publication_date': fields.Datetime.now()
        })
        return True

    # ----------------------------------------------------------------------------
    # Business Methods
    # ----------------------------------------------------------------------------

    def _name_get_fields(self):
        self.ensure_one()
        return ['employee_id', 'role_id', 'name']

    def _get_domain_template_slots(self):
        domain = ['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)]
        if self.role_id:
            domain += ['|', ('role_id', '=', self.role_id.id), ('role_id', '=', False)]
        return domain

    # ----------------------------------------------------------------------------
    # Print Report Methods
    # ----------------------------------------------------------------------------

    def _report_get_date_range(self):
        date_start = min(self.mapped('date_from'))
        date_stop = max(self.mapped('date_to'))
        return (fields.Datetime.from_string(date_start), fields.Datetime.from_string(date_stop))

    def _report_get_ranges(self, date_start, date_stop, scale):
        """ Note: all 3 parameters can be None """
        default_start, default_stop = self._report_get_date_range()

        date_start = date_start or default_start
        date_stop = date_stop or default_stop
        scale = scale or 'day'  # TODO: find a way to  compute a default scale

        # TODO here should the conversion of start/stop into current user tz

        date_start = date_utils.start_of(date_start, scale)
        date_stop = date_utils.end_of(date_stop, scale)

        ranges = []
        scale_delta = date_utils.get_timedelta(1, scale)
        current = date_start
        while current <= date_stop:
            ranges.append((current, current + scale_delta))
            current += scale_delta
        return ranges

    def _report_get_shift_in_range(self, date_start, date_stop, groupby_role=True):
        """
            returns a dict
                - key is the ID of the relationnal field `groupby`
                - value is a list of planning.shift record. If possible ordered by date_start ASC
        """
        groupby_field = 'role_id' if groupby_role else 'employee_id'
        group_map = {}
        for shift in self:
            if shift.date_from <= date_stop and shift.date_to >= date_start:
                groupby_key = shift[groupby_field]
                group_map.setdefault(groupby_key, [])

                if groupby_role:
                    label = shift.employee_id.display_name if shift.employee_id else ''
                else:
                    label = shift.role_id.name

                shift_slice = ShiftSlice(
                    start=max(shift.date_from, date_start),
                    stop=min(shift.date_to, date_stop),
                    label=label,
                    shift=shift
                )
                group_map[groupby_key].append(shift_slice)

        for dummy, values in group_map.items():
            values.sort(key=lambda shift_slice: shift_slice.shift.date_from)
        return group_map

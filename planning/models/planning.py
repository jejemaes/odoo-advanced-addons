# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
import pytz
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, format_datetime


class Planning(models.Model):
    _name = 'planning.planning'
    _description = "Planning Schedule"
    _order = 'date_start DESC'

    def _default_access_token(self):
        return uuid.uuid4().hex

    name = fields.Char("Name", required=True)
    access_token = fields.Char("Access Token", default=_default_access_token, copy=False, readonly=True)
    date_start = fields.Datetime("Start Date", required=True)
    date_stop = fields.Datetime("Stop Date", required=True)
    user_id = fields.Many2one('res.users', string="Responsible", default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    planning_type = fields.Selection(string='Type', required=True, selection=[('employee', 'Employee')], default='employee')
    include_open_shift = fields.Boolean("Include Open Shifts", help="Open shifts of the planning period will be exposed to employees and they can assign themselves.")
    description = fields.Text("Description", help="This is displayed on the planning web page")
    shift_count = fields.Integer("Shift Count", compute='_compute_shift_count')
    active = fields.Boolean(default=True, help="Set active to false to hide the planning without removing it.")
    display_mode = fields.Selection(string="Display Mode", compute='_compute_display_mode', selection=[('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')])

    @api.depends('date_start', 'date_stop', 'name')
    def _compute_display_name(self):
        """ This override is need to have a human readable string in the email light layout
            header (`message.record_name`).
        """
        for planning in self:
            tz = pytz.timezone(self.env.user.tz or 'UTC')
            start_datetime = pytz.utc.localize(planning.date_start).astimezone(tz).replace(tzinfo=None)
            end_datetime = pytz.utc.localize(planning.date_stop).astimezone(tz).replace(tzinfo=None)
            planning.display_name = _('%s (from %s to %s)') % (planning.name, format_date(self.env, start_datetime), format_date(self.env, end_datetime))

    @api.depends('date_start', 'date_stop', 'include_open_shift', 'planning_type')
    def _compute_shift_count(self):
        for planning in self:
            planning.shift_count = self.env['planning.shift'].search_count(planning.get_shift_domain())

    @api.depends('date_start', 'date_stop')
    def _compute_display_mode(self):
        for planning in self:
            if planning.date_start and planning.date_stop:
                delta = planning.date_stop - planning.date_start
                duration_hours = delta.total_seconds() / 3600.0
                if duration_hours <= 24:
                    planning.display_mode = 'day'
                elif duration_hours <= 24 * 7:
                    planning.display_mode = 'week'
                elif duration_hours <= 24 * 31:
                    planning.display_mode = 'month'
                else:
                    planning.display_mode = 'year'
            else:
                planning.display_mode = 'month'

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start and not self.date_stop:
            date_start = fields.Datetime.from_string(self.date_start)
            self.date_stop = date_start + self.company_id.planning_get_default_planning_timedelta()

    # ----------------------------------------------------------------------------
    # Actions
    # ----------------------------------------------------------------------------

    def action_view_shifts(self):
        return {
            'name': _('Shifts'),
            'res_model': 'planning.shift',
            'type': 'ir.actions.act_window',
            'views': [(False, 'gantt'), (False, 'calendar'), (False, 'list'), (False, 'form')],
            'view_mode': 'gantt,calendar,tree,form',
            'domain': self.get_shift_domain(),
            'context': {
                'default_planning_id': self.id,
                'gantt_initial_date': self.date_start,
                'gantt_scale': self.display_mode
            }
        }

    # ----------------------------------------------------------------------------
    # Business Methods
    # ----------------------------------------------------------------------------

    def get_shift_domain(self):
        domain = ['&', ('date_to', '>', self.date_start), ('date_from', '<', self.date_stop)]
        if not self.include_open_shift:
            domain = ['&'] + domain + [('resource_id', '!=', None)]
        return domain

    def get_planning_data_for_shift(self):
        """ Additionnal data for shift creation, when generate a shift from a planning sheet. Should be extended in other modules."""
        return {}

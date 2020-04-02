# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Role(models.Model):
    _name = 'planning.role'
    _description = 'Planning Role'
    _order = 'name desc'

    name = fields.Char("Title", required=True)
    color = fields.Integer("Color", default=0)
    description = fields.Char("Description")


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
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)

    publication_date = fields.Datetime("Last Publication Date", copy=False, readonly=True)
    include_open_shift = fields.Boolean("Include Open Shifts", help="Open shifts of the planning period will be exposed to employees and they can assign themselves.")
    shift_count = fields.Integer("Shift Count", compute='_compute_shift_count')

    @api.depends('date_start', 'date_stop')
    def _compute_shift_count(self):
        data = {}
        if self.ids:
            query = """
                SELECT t.planning_id, COUNT(t.resource_time_id) AS shift_count
                FROM (
                    SELECT R.id AS resource_time_id, P.id AS planning_id
                    FROM resource_calendar_leaves R
                        INNER JOIN planning_planning P ON (R.date_to > P.date_start AND R.date_from < P.date_stop)
                    WHERE R.time_type = 'planning' AND Pid IN %s
                ) AS t
                GROUP BY t.planning_id
            """
            self.env.cr.execute(query, (tuple(self.ids),))
            data = {item['planning_id']: item['shift_count'] for item in self.env.cr.dictfetchall()}

        for planning in self:
            planning.shift_count = data.get(planning.id, 0)

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start and not self.date_stop:
            date_start = fields.Datetime.from_string(self.date_start)
            self.date_stop = date_start + self.company_id.planning_get_default_planning_timedelta()

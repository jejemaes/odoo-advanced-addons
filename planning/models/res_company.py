# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class Company(models.Model):
    _inherit = 'res.company'

    planning_default_shift_duration = fields.Integer("Default Shift Duration", default=1)
    planning_default_shift_uom = fields.Selection([
        ('hour', 'Hour'),
        ('day', 'Day'),
    ], string="Default Shift Time Unit", default='hour', required=True)

    planning_default_planning_duration = fields.Integer("Default Planning Duration", default=1)
    planning_default_planning_uom = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
    ], string="Default Planning Time Unit", default='week', required=True)

    def planning_get_default_shift_timedelta(self):
        if self.planning_default_shift_uom == 'hour':
            return relativedelta(hours=self.planning_default_shift_duration or 0)
        return relativedelta(days=self.planning_default_shift_duration or 0)

    def planning_get_default_planning_timedelta(self):
        if self.planning_default_planning_uom == 'day':
            return relativedelta(days=self.planning_default_planning_duration or 0)
        if self.planning_default_planning_uom == 'week':
            return relativedelta(weeks=self.planning_default_planning_duration or 0)
        return relativedelta(months=self.planning_default_planning_duration or 0)

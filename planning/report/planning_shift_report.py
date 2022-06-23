# -*- coding: utf-8 -*-

import calendar

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import date_utils


class PlanningShiftReport(models.AbstractModel):
    _name = 'report.planning.report_planning_shift'
    _description = "Planning Shifts Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        # Note: docids is None, the real ones are in data. Don't know why.
        shifts = self.env['planning.shift'].browse(docids or data.get('doc_ids', []))

        # determine options
        report_title = data.get('report_title')
        scale = data.get('Scale') or 'day'

        data = {
            'doc_ids': shifts.ids,
            'doc_model': shifts._name,
            'docs': shifts,
            # options
            'report_title': report_title,
            'dt_format': self._compute_shift_dt_format(scale),
            'group_by_mode': data.get('group_by_mode', 'role'),
            # helpers
            'format_datetime': lambda dt, dt_format: tools.format_datetime(self.env, fields.Datetime.from_string(dt), dt_format=dt_format),
        }
        return data

    def _compute_shift_dt_format(self, scale):
        if scale == 'day':
            return 'HH:mm'
        if scale == 'week':
            return 'long'
        return 'full'

    def _compute_scale(self, date_start, date_stop):
        delta = date_stop - date_start
        duration_hours = delta.total_seconds() / 3600.0
        if duration_hours <= 24:
            return 'day'
        elif duration_hours <= 24 * 7:
            return 'week'
        return 'month'

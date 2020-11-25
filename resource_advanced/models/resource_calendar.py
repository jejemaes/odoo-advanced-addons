# -*- coding: utf-8 -*-

import copy
from collections import defaultdict
from datetime import datetime, time, timedelta
from itertools import groupby
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

from odoo.addons.resource.models.resource import Intervals
from odoo.addons.resource.models.resource_mixin import timezone_datetime


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.model
    def _default_working_day_ids(self):
        return self.env['resource.day'].search([])

    attendance_mode = fields.Selection([
        ('shift_per_day', 'Shift per Day'),
        ('full_day', 'Full Day'),
    ], string="Attendance Mode", default='shift_per_day', required=True)
    working_day_ids = fields.Many2many('resource.day', 'resource_calendar_attendance_day_rel', 'resource_calendar_id', 'resource_day_id', "Full Working Days")

    @api.onchange('attendance_mode')
    def _onchange_attendance_mode(self):
        if self.attendance_mode == 'shift_per_day':
            self.working_day_ids = None
            self.attendance_ids = self.default_get(['attendance_ids'])['attendance_ids']
        elif self.attendance_mode == 'full_day':
            self.two_weeks_calendar = False
            self.attendance_ids = None
            self.working_day_ids = self._default_working_day_ids()

    @api.onchange('attendance_ids', 'two_weeks_calendar', 'attendance_mode')
    def _onchange_hours_per_day(self):
        super(ResourceCalendar, self)._onchange_hours_per_day()
        if self.attendance_mode == 'full_day':
            self.hours_per_day = 24.0

    @api.constrains('two_weeks_calendar', 'attendance_mode')
    def _check_attendance_mode(self):
        for calendar in self:
            if calendar.attendance_mode == 'full_day':
                if calendar.two_weeks_calendar:
                    raise ValidationError(_("A Full day work calendar can not have the 2 weeks mode activated."))
                if not calendar.working_day_ids:
                    raise ValidationError(_("A Full day work calendar must have working days defined."))

    # --------------------------------------------------
    # Computation API
    # --------------------------------------------------

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        assert start_dt.tzinfo and end_dt.tzinfo

        if self.attendance_mode == 'full_day':
            resources_list = list(resources) + [self.env['resource.resource']]
            resource_ids = [r.id for r in resources_list]
            weekday_map = {day.dayofweek: day for day in self.working_day_ids}

            # for each attendance spec, generate the intervals in the date range
            result = dict.fromkeys(resource_ids, list())
            for resource in resources_list:
                # express all dates and times in specified tz or in the resource's timezone
                tz = tz if tz else timezone((resource or self).tz)
                resource_start_dt = start_dt.astimezone(tz)
                resource_end_dt = end_dt.astimezone(tz)

                period_start = resource_start_dt.replace(hour=0, minute=0, second=0)
                period_stop = resource_end_dt.replace(hour=23, minute=59, second=59) + timedelta(seconds=1)

                interval_tuples = []
                current_start = False
                current_stop = False
                # explore each day of the given period
                while period_start < period_stop:
                    # update slot start and/or stop
                    if period_start.weekday()+1 in weekday_map.keys():
                        if not current_start:
                            current_start = max(period_start, resource_start_dt)
                    else:
                        if not current_stop and current_start:
                            current_stop = min(period_start.replace(hour=0, minute=0, second=0), resource_end_dt)
                    # create the slot if needed
                    if current_start and current_stop:
                        interval_tuples.append([current_start, current_stop, self.env['resource.calendar.attendance']])
                        current_start = False
                        current_stop = False
                    period_start += timedelta(days=1)

                # if the last slot is still open, then close it. If the stop dt was a none working day, it
                # would have been closed in the loop.
                if current_start and not current_stop:
                    interval_tuples.append([current_start, end_dt, self.env['resource.calendar.attendance']])  # empty attendance as we are not using that model here

                result[resource.id] = interval_tuples

            return {r.id: Intervals(result[r.id]) for r in resources_list}

        return super(ResourceCalendar, self)._attendance_intervals_batch(start_dt, end_dt, resources=resources, domain=domain, tz=tz)

    def _work_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the effective work intervals between the given datetimes, in UTC.
            :param start_dt: UTC datetime as beginning of period
            :param end_dt: UTC datetime as end of period
            :param domain: domain of 'leaves' to take into account
        """
        if not domain:
            domain = self.env['resource.calendar.leaves'].get_leave_domain()
        return super(ResourceCalendar, self)._work_intervals_batch(start_dt, end_dt, resources=resources, domain=domain, tz=tz)

    def _unavailable_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the unavailable intervals between the given datetimes, in UTC.
            :param start_dt: UTC datetime as beginning of period
            :param end_dt: UTC datetime as end of period
            :param domain: domain of 'resrouce.time' to take into account
        """
        if not domain:
            domain = self.env['resource.calendar.leaves'].get_unavailable_domain()
        return super(ResourceCalendar, self)._unavailable_intervals_batch(start_dt, end_dt, resources=resources, domain=domain, tz=tz)

    def _available_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the effective work intervals between the given datetimes. """
        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources)

        attendance_intervals = self._attendance_intervals_batch(start_dt, end_dt, resources, tz=tz)
        unavailable_intervals_tuple_map = self._unavailable_intervals_batch(start_dt, end_dt, resources, domain, tz=tz)

        unavailable_intervals = {}
        for resource_id, tuple_list in unavailable_intervals_tuple_map.items():
            unavailable_intervals[resource_id] = Intervals([(start, stop, self.env['resource.calendar.attendance']) for start, stop in tuple_list])

        return {
            r.id: (attendance_intervals[r.id] - unavailable_intervals[r.id]) for r in resources_list
        }


class ResourceTime(models.Model):
    _inherit = 'resource.calendar.leaves'

    duration_hours = fields.Float("Duration (hours)", compute='_compute_durations', store=True, help="Duration expressed in hours, calculated with the working calendar (if set).")
    duration_days = fields.Float("Duration (days)", compute='_compute_durations', store=True, help="Duration expressed in days, calculated with the working calendar (if set).")

    _sql_constraints = [
        ('dates_chronological', "CHECK(date_from < date_to)", 'The start date must be smaller than its stop date.'),
    ]

    @api.depends('date_from', 'date_to', 'calendar_id')
    def _compute_durations(self):
        for resource_time in self:
            if resource_time.calendar_id:
                duration_data = resource_time.calendar_id.get_work_duration_data(resource_time.date_from, resource_time.date_to, compute_leaves=True)
                resource_time.duration_hours = duration_data['hours']
                resource_time.duration_days = duration_data['days']
            else:
                delta = resource_time.date_to - resource_time.date_from
                resource_time.duration_hours = delta.total_seconds() / 3600.0
                resource_time.duration_days = delta.days

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        """ As we set a SQL constraint, we can remove this soft constraint. However, we even need to remove it, since
            applying a `write` for date_from and date_to fields will trigger the python constraint due to the fact those
            fields are only update one by one, leading to date_to < date_from. Even a `flush` did not solve this.
            This is probably a mystery of the new ORM v14.0 ...
        """
        return True

    def _get_overlap_data(self, time_types=None):
        """ Get the ids of the overlapping time slot, mathcing the given time types."""
        if not time_types:
            time_types = self._fields['time_type'].get_values()

        overlap_map = dict.fromkeys(self.ids, list())
        if self.ids:
            query = """
                SELECT t.time_id AS time_id, COUNT(t.time_overlap_id) AS overlap_count, ARRAY_AGG(t.time_overlap_id) AS overlap_ids
                FROM (
                    SELECT R1.id AS time_id, R2.id AS time_overlap_id
                    FROM resource_calendar_leaves R1
                        INNER JOIN resource_calendar_leaves R2 ON (R1.date_to > R2.date_from AND R1.date_from < R2.date_to AND R1.id != R2.id)
                    WHERE R1.time_type in %s
                        AND R2.time_type in %s
                        AND R1.resource_id = R2.resource_id
                        AND R1.id IN %s
                ) AS t
                GROUP BY t.time_id
            """
            self.env.cr.execute(query, (tuple(time_types), tuple(time_types), tuple(self.ids),))
            data = self.env.cr.dictfetchall()
            overlap_map.update({item['time_id']: item['overlap_ids'] for item in data})
        return overlap_map

    @api.model
    def get_unavailable_domain(self):
        return [('time_type', '=', 'leave')]

    @api.model
    def get_leave_domain(self):
        return [('time_type', '=', 'leave')]

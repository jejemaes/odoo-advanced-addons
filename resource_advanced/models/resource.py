# -*- coding: utf-8 -*-

import copy
from datetime import datetime, time, timedelta
from itertools import groupby
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.resource.models.resource import Intervals
from odoo.osv import expression


def timezone_datetime(time):
    if not time.tzinfo:
        time = time.replace(tzinfo=utc)
    return time


def assemble_intervals(interval_list):
    result = []
    for interval in interval_list:
        for start, stop, meta in interval:
            result.append((start, stop, meta))
    return Intervals(result)


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    hour_from = fields.Float(default=0.0)
    hour_to = fields.Float(default=0.0)
    attendance_mode = fields.Selection(related='calendar_id.attendance_mode', store=True)
    is_working_day = fields.Boolean("Is Full Working Day")

    def create(self, value_list):
        """ Force the name of attendance for full-day mode. """
        calendar_ids = [vals['calendar_id'] for vals in value_list]
        calendar_map = {calendar.id: calendar for calendar in self.env['resource.calendar'].browse(calendar_ids)}
        attendance_labels = dict(self.env['resource.calendar.attendance']._fields['dayofweek']._description_selection(self.env))
        for vals in value_list:
            if not vals.get('name'):
                calendar = calendar_map[vals['calendar_id']]
                if calendar.attendance_mode == 'full_day':
                    vals['name'] = attendance_labels.get(vals.get('dayofweek'), 'Unknown day of week')
                    for fname in ['day_period', 'hour_from', 'hour_to']:  # let the default values filled those required field, since they are not relevant for full-day mode
                        if fname in vals:
                            del vals[fname]
        return super(ResourceCalendarAttendance, self).create(value_list)


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.model
    def _default_attendance_day_ids(self):
        return [
            (0, 0, {'dayofweek': '0', 'is_working_day': True}),
            (0, 0, {'dayofweek': '1', 'is_working_day': True}),
            (0, 0, {'dayofweek': '2', 'is_working_day': True}),
            (0, 0, {'dayofweek': '3', 'is_working_day': True}),
            (0, 0, {'dayofweek': '4', 'is_working_day': True}),
            (0, 0, {'dayofweek': '5', 'is_working_day': True}),
            (0, 0, {'dayofweek': '6', 'is_working_day': True}),
        ]

    attendance_mode = fields.Selection([
        ('shift_per_day', 'Shift per Day'),
        ('full_day', 'Full Day'),
    ], string="Attendance Mode", default='shift_per_day', required=True)

    @api.onchange('attendance_mode')
    def _onchange_attendance_mode(self):
        if self.attendance_mode == 'shift_per_day':
            self.attendance_ids = False
            self.attendance_ids = self._get_default_attendance_ids()
        elif self.attendance_mode == 'full_day':
            self.attendance_ids = False
            self.attendance_ids = self._default_attendance_day_ids()

    @api.constrains('attendance_mode', 'attendance_ids')
    def _check_attendances(self):
        for calendar in self:
            if calendar.attendance_mode == 'full_day':
                for dayofweek, attendances in groupby(self.attendance_ids, lambda l: l.dayofweek):
                    if len(list(attendances)) >= 2:
                        raise ValidationError(_("In a full-dayy working calendar, a week day can only be set up once."))

    # --------------------------------------------------
    # Computation API
    # --------------------------------------------------

    def _attendance_intervals(self, start_dt, end_dt, resource=None):
        """ Return the attendance intervals in the given datetime range.
            The returned intervals are expressed in the resource's timezone.
        """
        assert start_dt.tzinfo and end_dt.tzinfo

        if self.attendance_mode == 'full_day':
            # express all dates and times in the resource's timezone
            tz = timezone((resource or self).tz)
            start_dt = start_dt.astimezone(tz)
            end_dt = end_dt.astimezone(tz)

            attendance_map = {att.dayofweek: att for att in self.attendance_ids.filtered('is_working_day')}
            working_weekdays = attendance_map.keys()

            period_start = start_dt.replace(hour=0, minute=0, second=0)
            period_stop = end_dt.replace(hour=23, minute=59, second=59) + timedelta(seconds=1)

            result = []
            attendances = self.env['resource.calendar.attendance']
            current_start = False
            current_stop = False
            # explore each day of the given period
            while period_start < period_stop:
                # update slot start and/or stop
                if str(period_start.weekday()) in working_weekdays:
                    attendances |= attendance_map[str(period_start.weekday())]
                    if not current_start:
                        current_start = max(period_start, start_dt)
                else:
                    if not current_stop and current_start:
                        current_stop = min(period_start.replace(hour=0, minute=0, second=0), end_dt)
                # create the slot if needed
                if current_start and current_stop:
                    result.append([current_start, current_stop, attendances])
                    attendances = self.env['resource.calendar.attendance']
                    current_start = False
                    current_stop = False
                period_start += timedelta(days=1)

            # if the last slot is still open, then close it. If the stop dt was a none working day, it
            # would have been closed in the loop.
            if current_start and not current_stop:
                result.append([current_start, end_dt, attendances])

            return Intervals(result)

        return super(ResourceCalendar, self)._attendance_intervals(start_dt, end_dt, resource=resource)

    def _period_interval(self, start_dt, end_dt, resource=None):
        tz = timezone((resource or self).tz)
        start_dt = start_dt.astimezone(tz)
        end_dt = end_dt.astimezone(tz)

        attendances = self.env['resource.calendar.attendance']
        return Intervals([[start_dt, end_dt, attendances]])

    def _unavailable_intervals(self, start_dt, end_dt, resource=None, domain=None):
        """ Allow to extend leaves domain as generic unavailable domain. """
        if domain is None:
            domain = self.env['resource.calendar.leaves'].get_unavailable_domain()

        period_interval = self._period_interval(start_dt, end_dt, resource=resource)
        work_intervals = self._work_intervals(start_dt, end_dt, resource=resource, domain=domain)
        return period_interval - work_intervals

    def _available_intervals(self, start_dt, end_dt, resource=None, domain=None):
        """ Return the current effective work intervals between the given datetimes, taking all time entries considered as unavailable. """
        return (self._attendance_intervals(start_dt, end_dt, resource) -
                self._unavailable_intervals(start_dt, end_dt, resource, domain))

    def _calendar_unavailibilities(self, start_dt, end_dt, resource_ids, domain=None):
        period_interval = self._period_interval(start_dt, end_dt)
        parent_unavailabilities = period_interval - self._work_intervals(start_dt, end_dt, resource=None, domain=domain)

        result = dict.fromkeys(resource_ids, list())
        for resource in self.env['resource.resource'].browse(resource_ids):
            # union of unavailable interval of both calendar
            resource_unavailabilities = period_interval - resource.calendar_id._work_intervals(start_dt, end_dt, resource=resource, domain=domain)
            result[resource.id] = assemble_intervals([parent_unavailabilities, resource_unavailabilities])
        return result

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def get_combined_unavailibilities(self, start_dt, end_dt, resource_ids, domain=None):
        """ Difference between 'self' calendar and resource'one unavailabilities. """
        start_dt = timezone_datetime(start_dt)
        end_dt = timezone_datetime(end_dt)
        if not domain:
            domain = self.env['resource.calendar.leaves'].get_unavailable_domain()

        unavailabilities_map = self._calendar_unavailibilities(start_dt, end_dt, resource_ids, domain=domain)

        result = {}
        for resource_id, intervals in unavailabilities_map.items():
            utc_intervals = [(start.astimezone(utc), stop.astimezone(utc)) for start, stop, meta in intervals]
            result[resource_id] = utc_intervals
        return result

    def get_unavailabilities(self, start_dt, end_dt, domain=None):
        start_dt = timezone_datetime(start_dt)
        end_dt = timezone_datetime(end_dt)

        result = []
        for start, stop, meta in self._unavailable_intervals(start_dt, end_dt, resource=None, domain=domain):
            result.append((start.astimezone(utc), stop.astimezone(utc)))
        return result


class Resource(models.Model):
    _inherit = 'resource.resource'

    color = fields.Integer("Color", default=1)
    leaves_count = fields.Integer("Number of leaves", compute='_compute_leaves_count')

    def _compute_leaves_count(self):
        domain = expression.AND([self.env['resource.calendar.leaves'].get_leave_domain(), [('resource_id', 'in', self.ids)]])
        grouped_data = self.env['resource.calendar.leaves'].read_group(domain, ['resource_id'], ['resource_id'])
        mapped_data = {db['resource_id'][0]: db['resource_id_count'] for db in grouped_data}
        for resource in self:
            resource.leaves_count = mapped_data.get(resource.id, 0)

    # --------------------------------------------------
    # Business Methods
    # --------------------------------------------------

    def is_available(self, start, end, domain=None):
        unavailable_map = self.get_unavailable_intervals(start, end, domain=domain)
        resource_mapping = {}
        for resource in self:
            resource_mapping[resource.id] = not bool(unavailable_map.get(resource.id, []))
        return resource_mapping

    def get_available_intervals(self, start, end, domain=None):
        """ get the available intevals for the current resources, expressed in UTC """
        start_datetime = timezone_datetime(start)
        end_datetime = timezone_datetime(end)

        resource_mapping = {}
        for resource in self:
            calendar = resource.calendar_id
            resource_available_intervals = calendar._available_intervals(start_datetime, end_datetime, resource, domain=domain)
            resource_available_intervals = [(start.astimezone(utc), stop.astimezone(utc)) for start, stop, meta in resource_available_intervals]
            resource_mapping[resource.id] = resource_available_intervals
        return resource_mapping

    def get_unavailable_intervals(self, start, end, domain=None):
        """ get the unavailbable intevals (slots where the resource has something to do like work, rental, ...) for the current resources, expressed in UTC """
        start_datetime = timezone_datetime(start)
        end_datetime = timezone_datetime(end)

        resource_mapping = {}
        for resource in self:
            calendar = resource.calendar_id
            resource_unavailable_intervals = calendar._unavailable_intervals(start_datetime, end_datetime, resource, domain=domain)
            resource_unavailable_intervals = [(start.astimezone(utc), stop.astimezone(utc)) for start, stop, meta in resource_unavailable_intervals]
            resource_mapping[resource.id] = resource_unavailable_intervals
        return resource_mapping

    # Commented as not tested, and not used yet
    #
    # def get_work_intervals(self, start, end):
    #     """ get the intevals when it is supposed to be work time for the current resources, expressed in UTC """
    #     from_datetime = timezone_datetime(start)
    #     to_datetime = timezone_datetime(end)
    #     domain = self.env['resource.calendar.leaves'].get_leave_domain()

    #     resource_mapping = {}
    #     for resource in self:
    #         calendar = resource.calendar_id
    #         resource_work_intervals = calendar._work_intervals(from_datetime, to_datetime, resource, domain)
    #         resource_work_intervals = [(start.astimezone(utc), stop.astimezone(utc)) for start, stop, meta in resource_work_intervals]
    #         resource_mapping[resource.id] = resource_work_intervals
    #     return resource_mapping

    # def get_leave_intervals(self, start, end):
    #     """ get the leave intevals for the current resources, expressed in UTC """
    #     from_datetime = timezone_datetime(start)
    #     to_datetime = timezone_datetime(end)
    #     domain = self.env['resource.calendar.leaves'].get_leave_domain()

    #     resource_mapping = {}
    #     for resource in self:
    #         calendar = resource.calendar_id
    #         resource_leave_intervals = calendar._leave_intervals(from_datetime, to_datetime, resource, domain)
    #         resource_leave_intervals = [(start.astimezone(utc), stop.astimezone(utc)) for start, stop, meta in resource_leave_intervals]
    #         resource_mapping[resource.id] = resource_leave_intervals
    #     return resource_mapping


class ResourceTime(models.Model):
    _inherit = 'resource.calendar.leaves'

    _sql_constraints = [
        ('dates_chronological', "CHECK(date_from < date_to)", 'The start date must be smaller than its stop date.'),
    ]

    @api.model
    def get_unavailable_domain(self):
        return [('time_type', '=', 'leave')]

    @api.model
    def get_leave_domain(self):
        return [('time_type', '=', 'leave')]

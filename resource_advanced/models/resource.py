# -*- coding: utf-8 -*-

import copy
from datetime import datetime, time, timedelta
from itertools import groupby
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.resource.models.resource import Intervals
from odoo.addons.resource.models.resource_mixin import timezone_datetime
from odoo.osv import expression


class Resource(models.Model):
    _inherit = 'resource.resource'

    color = fields.Integer("Color", default=1)
    leaves_count = fields.Integer("Number of leaves", compute='_compute_leaves_count')
    is_available = fields.Boolean("Is Available", compute='_compute_is_available', search='_search_is_available', help="Available means free for work (not leaves, during working time, not busy to anything else)")

    @api.depends('calendar_id')
    def _compute_leaves_count(self):
        domain = expression.AND([self.env['resource.calendar.leaves'].get_leave_domain(), [('resource_id', 'in', self.ids)]])
        grouped_data = self.env['resource.calendar.leaves'].read_group(domain, ['resource_id'], ['resource_id'])
        mapped_data = {db['resource_id'][0]: db['resource_id_count'] for db in grouped_data}
        for resource in self:
            resource.leaves_count = mapped_data.get(resource.id, 0)

    @api.depends_context('resource_start_dt', 'resource_end_dt')
    def _compute_is_available(self):
        """ Note: context date are expressed in UTC as we need to compare them to resource time in database. """
        start_dt = self.env.context.get('resource_start_dt')
        end_dt = self.env.context.get('resource_stop_dt')
        if start_dt and end_dt:
            start = timezone_datetime(fields.Datetime.from_string(start_dt))
            stop = timezone_datetime(fields.Datetime.from_string(end_dt))
            unavailable_map = self.get_unavailable_intervals(start, stop)
            for resource in self:
                resource.is_available = bool(unavailable_map.get(resource.id, False))
        else:
            for resource in self:
                resource.is_available = True

    @api.model
    def _search_is_available(self, operator, value):
        """ Note: context date are expressed in UTC as we need to compare them to resource time in database. """
        start_dt = self.env.context.get('resource_start_dt')
        end_dt = self.env.context.get('resource_stop_dt')
        if start_dt and end_dt:
            # resource time linked to resources
            query = """
                SELECT RCL.resource_id
                FROM resource_calendar_leaves RCL
                WHERE resource_id IS NOT NULL
                    AND ( (%s <= date_from AND date_from <= %s) OR (%s <= date_to AND date_to <= %s) )
            """
            operator_new = 'not inselect'
            if operator in expression.NEGATIVE_TERM_OPERATORS or not value:
                operator_new = 'inselect'

            domain = [('id', operator_new, (query, (start_dt, end_dt, start_dt, end_dt)))]
            # TODO : global leaves: calendar having a leaves on the given period
            # query = ...
            # domain = expression.AND([domain, [('calendar_id', 'select_operator', query)]])
        else:
            domain = []  # no resource available if no dates
        return domain

    # --------------------------------------------------
    # Business Methods
    # --------------------------------------------------

    def get_available_intervals(self, start, end, domain=None):
        """ get the available intevals for the current resources, expressed in UTC """
        start_datetime = timezone_datetime(start)
        end_datetime = timezone_datetime(end)

        calendar_map = {}
        for resource in self:
            if resource.calendar_id not in calendar_map:
                calendar_map[resource.calendar_id] = self.env['resource.resource']
            calendar_map[resource.calendar_id] |= resource

        # restore as dates tuple, in UTC
        result = {}
        for calendar, resources in calendar_map.items():
            interval_map = calendar._available_intervals_batch(start, end, resources=resources, domain=domain)
            for resource_id, intervals in interval_map.items():
                result[resource_id] = [(start.astimezone(utc), stop.astimezone(utc)) for start, stop, meta in intervals]

        return result

    def get_unavailable_intervals(self, start, end, domain=None):
        """ get the unavailbable intevals (slots where the resource has something to do like
            work, rental, ...) for the current resources, expressed in UTC
        """
        start_datetime = timezone_datetime(start)
        end_datetime = timezone_datetime(end)

        calendar_map = {}
        for resource in self:
            if resource.calendar_id not in calendar_map:
                calendar_map[resource.calendar_id] = self.env['resource.resource']
            calendar_map[resource.calendar_id] |= resource

        result = {}
        for calendar, resources in calendar_map.items():
            interval_map = calendar._unavailable_intervals_batch(start, end, resources=resources, domain=domain)

            # convert intervals tuple into Intervals object as `unavailable_intervals_batch` in resource module does not return `Intervals` object.
            unavailable_intervals = {}
            for resource_id, tuple_list in interval_map.items():
                unavailable_intervals[resource_id] = Intervals([(start, stop, self.env['resource.calendar.attendance']) for start, stop in tuple_list])

            # restore as dates tuple, in UTC
            for resource_id, intervals in unavailable_intervals.items():
                result[resource_id] = [(start.astimezone(utc), stop.astimezone(utc)) for start, stop, meta in intervals]

        return result

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from pytz import timezone, utc

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.addons.resource.models.resource import Intervals
from odoo.addons.resource.tests.common import TestResourceCommon
from odoo.addons.resource.tests.test_resource import datetime_tz, datetime_str
from odoo.tests.common import TransactionCase


class TestCalendarAdvanced(TransactionCase):

    def setUp(self):
        super(TestCalendarAdvanced, self).setUp()

        self.calendar_eur = self.env['resource.calendar'].create({
            'name': "5 days week",
            'tz': 'Europe/Brussels',
            'attendance_mode': 'full_day',
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'is_working_day': True}),
                (0, 0, {'dayofweek': '1', 'is_working_day': True}),
                (0, 0, {'dayofweek': '2', 'is_working_day': True}),
                (0, 0, {'dayofweek': '3', 'is_working_day': True}),
                (0, 0, {'dayofweek': '4', 'is_working_day': True}),
                (0, 0, {'dayofweek': '5', 'is_working_day': False}),
                (0, 0, {'dayofweek': '6', 'is_working_day': False}),
            ],
        })

        # self.calendar_america = self.env['resource.calendar'].create({
        #     'name': "7/7 days",
        #     'tz': 'America/Los_Angeles',
        #     'attendance_mode': 'full_day',
        #     'attendance_ids': [
        #         (0, 0, {'dayofweek': '0', 'is_working_day': True}),
        #         (0, 0, {'dayofweek': '1', 'is_working_day': True}),
        #         (0, 0, {'dayofweek': '2', 'is_working_day': True}),
        #         (0, 0, {'dayofweek': '3', 'is_working_day': True}),
        #         (0, 0, {'dayofweek': '4', 'is_working_day': True}),
        #         (0, 0, {'dayofweek': '5', 'is_working_day': True}),
        #         (0, 0, {'dayofweek': '6', 'is_working_day': True}),
        #     ],
        # })

        # Employee is linked to a resource.resource via resource.mixin
        self.resource_eur = self.env['resource.test'].create({
            'name': 'Jean',
            'resource_calendar_id': self.calendar_eur.id,
        })
        # self.resource_america = self.env['resource.test'].create({
        #     'name': 'Patel',
        #     'resource_calendar_id': self.calendar_america.id,
        # })

    def test_available_intervals(self):
        # From monday to sunday 2 weeks after
        start = datetime_tz(2020, 5, 4, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 17, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_available_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 3, 22, 0, tzinfo=utc), datetime(2020, 5, 8, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 10, 22, 0, tzinfo=utc), datetime(2020, 5, 15, 22, 0, tzinfo=utc))
        ])
        # From saturday to Wednesday in 2 weeks
        start = datetime_tz(2020, 5, 9, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 20, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_available_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 10, 22, 0, tzinfo=utc), datetime(2020, 5, 15, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 17, 22, 0, tzinfo=utc), datetime(2020, 5, 19, 22, 0, tzinfo=utc))
        ])
        # From Wednesday to saturday in 2 weeks
        start = datetime_tz(2020, 5, 6, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 16, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_available_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 5, 22, 0, tzinfo=utc), datetime(2020, 5, 8, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 10, 22, 0, tzinfo=utc), datetime(2020, 5, 15, 22, 0, tzinfo=utc))
        ])

    def test_available_intervals_with_leaves(self):
        # the leave, only Wednesday morning
        self.env['resource.calendar.leaves'].create({
            'name': 'leave for resource eur',
            'calendar_id': self.calendar_eur.id,
            'resource_id': self.resource_eur.resource_id.id,
            'date_from': datetime_str(2020, 5, 13, 8, 0, 0, tzinfo=self.resource_eur.resource_id.tz),
            'date_to': datetime_str(2020, 5, 13, 13, 30, 00, tzinfo=self.resource_eur.resource_id.tz),
        })

        # From monday to sunday 2 weeks after
        start = datetime_tz(2020, 5, 4, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 17, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_available_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 3, 22, 0, tzinfo=utc), datetime(2020, 5, 8, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 10, 22, 0, tzinfo=utc), datetime(2020, 5, 13, 6, 0, tzinfo=utc)),
            (datetime(2020, 5, 13, 11, 30, tzinfo=utc), datetime(2020, 5, 15, 22, 0, tzinfo=utc)),
        ])
        # From saturday to Wednesday in 2 weeks
        start = datetime_tz(2020, 5, 9, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 20, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_available_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 10, 22, 0, tzinfo=utc), datetime(2020, 5, 13, 6, 0, tzinfo=utc)),
            (datetime(2020, 5, 13, 11, 30, tzinfo=utc), datetime(2020, 5, 15, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 17, 22, 0, tzinfo=utc), datetime(2020, 5, 19, 22, 0, tzinfo=utc)),
        ])
        # From Wednesday to saturday in 2 weeks
        start = datetime_tz(2020, 5, 6, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 16, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_available_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 5, 22, 0, tzinfo=utc), datetime(2020, 5, 8, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 10, 22, 0, tzinfo=utc), datetime(2020, 5, 13, 6, 0, tzinfo=utc)),
            (datetime(2020, 5, 13, 11, 30, tzinfo=utc), datetime(2020, 5, 15, 22, 0, tzinfo=utc)),
        ])

    def test_unavailable_intervals(self):
        # From monday to sunday 2 weeks after
        start = datetime_tz(2020, 5, 4, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 17, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 10, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 15, 22, 0, tzinfo=utc), datetime(2020, 5, 16, 22, 0, tzinfo=utc))
        ])
        # From saturday to Wednesday in 2 weeks
        start = datetime_tz(2020, 5, 9, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 20, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 10, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 15, 22, 0, tzinfo=utc), datetime(2020, 5, 17, 22, 0, tzinfo=utc))
        ])
        # From Wednesday to sunday in 2 weeks
        start = datetime_tz(2020, 5, 6, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 17, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 10, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 15, 22, 0, tzinfo=utc), datetime(2020, 5, 16, 22, 0, tzinfo=utc))
        ])


    def test_unavailable_intervals_with_leaves(self):
        # the leave, only Wednesday morning
        self.env['resource.calendar.leaves'].create({
            'name': 'leave for resource eur',
            'calendar_id': self.calendar_eur.id,
            'resource_id': self.resource_eur.resource_id.id,
            'date_from': datetime_str(2020, 5, 13, 8, 0, 0, tzinfo=self.resource_eur.resource_id.tz),
            'date_to': datetime_str(2020, 5, 13, 13, 30, 00, tzinfo=self.resource_eur.resource_id.tz),
        })
        # From monday to sunday 2 weeks after
        start = datetime_tz(2020, 5, 4, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 17, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 10, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 13, 6, 0, tzinfo=utc), datetime(2020, 5, 13, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 15, 22, 0, tzinfo=utc), datetime(2020, 5, 16, 22, 0, tzinfo=utc)),
        ])
        # From saturday to Wednesday in 2 weeks
        start = datetime_tz(2020, 5, 9, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 20, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 10, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 13, 6, 0, tzinfo=utc), datetime(2020, 5, 13, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 15, 22, 0, tzinfo=utc), datetime(2020, 5, 17, 22, 0, tzinfo=utc)),
        ])
        # From Wednesday to sunday in 2 weeks
        start = datetime_tz(2020, 5, 6, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 17, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 10, 22, 0, tzinfo=utc)),
            (datetime(2020, 5, 13, 6, 0, tzinfo=utc), datetime(2020, 5, 13, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 15, 22, 0, tzinfo=utc), datetime(2020, 5, 16, 22, 0, tzinfo=utc)),
        ])

        # the leave right after a none working day
        self.env['resource.calendar.leaves'].create({
            'name': 'leave for resource eur',
            'calendar_id': self.calendar_eur.id,
            'resource_id': self.resource_eur.resource_id.id,
            'date_from': datetime_str(2020, 5, 11, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz),
            'date_to': datetime_str(2020, 5, 11, 13, 30, 00, tzinfo=self.resource_eur.resource_id.tz),
        })
        # /!\ the other leave is still there !
        # From thursday to the next one
        start = datetime_tz(2020, 5, 7, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 14, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 11, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 13, 6, 0, tzinfo=utc), datetime(2020, 5, 13, 11, 30, tzinfo=utc)),
        ])
        # From saturday to wednesday
        start = datetime_tz(2020, 5, 9, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 14, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 11, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 13, 6, 0, tzinfo=utc), datetime(2020, 5, 13, 11, 30, tzinfo=utc)),
        ])
        # From monday (day of) to sunday
        start = datetime_tz(2020, 5, 11, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 18, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 10, 22, 0, tzinfo=utc), datetime(2020, 5, 11, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 13, 6, 0, tzinfo=utc), datetime(2020, 5, 13, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 15, 22, 0, tzinfo=utc), datetime(2020, 5, 17, 22, 0, tzinfo=utc)),
        ])

        # leaves during non working days
        self.env['resource.calendar.leaves'].create({
            'name': 'leave for resource eur',
            'calendar_id': self.calendar_eur.id,
            'resource_id': self.resource_eur.resource_id.id,
            'date_from': datetime_str(2020, 5, 10, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz),
            'date_to': datetime_str(2020, 5, 10, 13, 30, 00, tzinfo=self.resource_eur.resource_id.tz),
        })
         # /!\ the other leave is still there !
        # From thursday to the next one
        start = datetime_tz(2020, 5, 7, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 14, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 11, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 13, 6, 0, tzinfo=utc), datetime(2020, 5, 13, 11, 30, tzinfo=utc)),
        ])
        # From saturday to wednesday
        start = datetime_tz(2020, 5, 9, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 14, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 8, 22, 0, tzinfo=utc), datetime(2020, 5, 11, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 13, 6, 0, tzinfo=utc), datetime(2020, 5, 13, 11, 30, tzinfo=utc)),
        ])
        # From monday (day of) to sunday
        start = datetime_tz(2020, 5, 11, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        stop = datetime_tz(2020, 5, 18, 0, 0, 0, tzinfo=self.resource_eur.resource_id.tz)
        intervals = self.resource_eur.resource_id.get_unavailable_intervals(start, stop)[self.resource_eur.resource_id.id]
        self.assertEqual(intervals, [
            (datetime(2020, 5, 10, 22, 0, tzinfo=utc), datetime(2020, 5, 11, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 13, 6, 0, tzinfo=utc), datetime(2020, 5, 13, 11, 30, tzinfo=utc)),
            (datetime(2020, 5, 15, 22, 0, tzinfo=utc), datetime(2020, 5, 17, 22, 0, tzinfo=utc)),
        ])

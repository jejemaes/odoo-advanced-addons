# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pytz

from odoo import api, fields, models


def _float_to_time(value):
    hours, minutes = divmod(abs(value) * 60, 60)
    minutes = round(minutes)
    if minutes == 60:
        minutes = 0
        hours += 1
    return hours, minutes


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def get_json_schedule(self, tz='Europe/Brussels'):
        tz_destination = pytz.timezone(tz)
        result = {}
        for calendar in self:
            schedule = dict.fromkeys(range(1, 7), False)

            # generate the list of datetime intervals (working slots) in the current week into the destination time
            now = datetime.now()
            monday = now - timedelta(days=now.weekday())

            schedule_utc = []
            if calendar.attendance_mode == 'full_day':
                for attendance in calendar.attendance_ids.filtered(lambda a: a.is_working_day).sorted(lambda a: a.dayofweek):
                    current = monday + timedelta(days=int(attendance.dayofweek))
                    begin = current.replace(hour=0, minute=0, second=0)
                    end = current.replace(hour=23, minute=59, second=59)
                    schedule_utc.append((pytz.timezone(calendar.tz).localize(begin).astimezone(tz_destination), pytz.timezone(calendar.tz).localize(end).astimezone(tz_destination)))

            elif calendar.attendance_mode == 'shift_per_day':
                for attendance in calendar.attendance_ids:
                    current = monday + timedelta(days=int(attendance.dayofweek))
                    hour_begin, minute_begin = _float_to_time(attendance.hour_from)
                    hour_end, minute_end = _float_to_time(attendance.hour_to)

                    begin = current.replace(hour=hour_begin, minute=minute_begin, second=0)
                    end = current.replace(hour=hour_end, minute=minute_end, second=0)

                    schedule_utc.append((pytz.timezone(calendar.tz).localize(begin).astimezone(tz_destination), pytz.timezone(calendar.tz).localize(end).astimezone(tz_destination)))


            # split the interval (no cross day slots)
            schedule_map_utc = {}
            for (begin, end) in schedule_utc:
                dow = begin.weekday() + 1
                current_end = min(begin.replace(hour=23, minute=59, second=59), end)
                schedule_map_utc.setdefault(dow, []).append((begin, current_end))

                if end != current_end:  # add the end of initial slot tomorrow
                    dow = end.weekday() + 1
                    schedule_map_utc.setdefault(dow, []).append((end.replace(hour=0, minute=0, second=0), end))

            # convert time into string, per day of week
            schedule = {}
            for dow, intervals in schedule_map_utc.items():
                schedule[dow] = []
                for (begin, end) in intervals:
                    begin_str = begin.strftime("%H:%M:%S")
                    end_str = end.strftime("%H:%M:%S")
                    schedule[dow].append((begin_str, end_str))

            result[calendar.id] = schedule
        return result

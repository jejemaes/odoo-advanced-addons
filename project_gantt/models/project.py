# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Task(models.Model):
    _inherit = 'project.task'

    planned_start_date = fields.Date("Planned Start Date", help="Start date for Gantt view")
    planned_stop_date = fields.Date("Planned Stop Date", help="Stop date for Gantt view")

    _sql_constraints = [
        ('planned_dates_chronological', "CHECK(planned_start_date <= planned_stop_date)", 'The planned start date must be smaller than its planned stop date.'),
        ('planned_stop_required', "CHECK((planned_stop_date IS NOT NULL AND planned_start_date IS NOT NULL) OR (planned_stop_date IS NULL))", 'If a task is planned, both start and stop dates are required.'),
    ]

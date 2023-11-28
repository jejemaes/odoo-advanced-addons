# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Task(models.Model):
    _inherit = 'project.task'

    planned_start_date = fields.Date("Planned Start Date", required=False, help="Start date for Gantt view")

    _sql_constraints = [
        ('planned_dates_chronological', "CHECK(planned_start_date <= date_deadline)", 'The planned start date must be smaller than its deadline.'),
    ]

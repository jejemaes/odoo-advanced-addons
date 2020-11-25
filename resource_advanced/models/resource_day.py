# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResourceDay(models.Model):
    _name = 'resource.day'
    _description = "Resource Day"
    _order = 'dayofweek ASC'

    name = fields.Char("Name", translate=True)
    dayofweek = fields.Integer("Weekday", default=0, help="Weekday index (1 is monday, ....)")
    shortname = fields.Char("Abbreviation", compute='_compute_shortname')

    _sql_constraints = [
        ('dayofweek_unique', "UNIQUE(dayofweek)", "Only one dayofweek"),
        ('dayofweek_range', "CHECK(dayofweek > 0 AND dayofweek <= 7)", "Weekday must be between 1 and 7"),
    ]

    @api.depends('dayofweek', 'name')
    def _compute_shortname(self):
        for day in self:
            day.shortname = day.name

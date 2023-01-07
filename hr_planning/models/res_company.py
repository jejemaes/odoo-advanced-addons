# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class Company(models.Model):
    _inherit = 'res.company'

    planning_allow_self_assign = fields.Boolean("Allow Employees to Assign Themselves")
    planning_allow_self_unassign = fields.Boolean("Allow Employees to Unassign Themselves")

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
   
    budget_tag_ids = fields.Many2many('budget.analytic.tag', string='Budget Tags')

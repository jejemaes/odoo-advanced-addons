# -*- coding: utf-8 -*-
from random import randint

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class BudgetAnalyticTag(models.Model):
    _name = 'budget.analytic.tag'
    _description = "Budget Analytic Tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color)


class BudgetLine(models.Model):
    _inherit = 'budget.budget.line'

    mode = fields.Selection(selection_add=[
        ('analytic', 'Analytic'),
    ], ondelete={'analytic': 'set default'})
    analytic_account_id = fields.Many2one('account.analytic.account')
    analytic_budget_tag_ids = fields.Many2many('budget.analytic.tag', string='Analytic Budget Tag')

    @api.depends('analytic_account_id', 'analytic_budget_tag_ids')
    def _compute_practical_amount(self):
        lines_by_analytic = self.filtered(lambda l: l.mode == 'analytic')
        lines_by_other = self.filtered(lambda l: l.mode != 'analytic')

        for line in lines_by_analytic: # TODO handle multi currency
            line.practical_amount = sum(self.env['account.analytic.line'].search(line._get_analytic_domain()).mapped('amount'))

        super(BudgetLine, lines_by_other)._compute_practical_amount()

    def _get_analytic_domain(self):
        self.ensure_one()

        domain = ['&', ('date', '>=', self.budget_id.date_from), ('date', '<=', self.budget_id.date_to)]
        if self.analytic_account_id:
            domain = expression.AND([domain, [('account_id', '=', self.analytic_account_id.id)]])
        if self.analytic_budget_tag_ids:
            domain = expression.AND([domain, [('budget_tag_ids', 'in', self.analytic_budget_tag_ids.ids)]])
        return domain

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    budget_line_ids = fields.One2many('budget.budget.line', 'analytic_account_id', 'Budget Lines')


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    budget_category_id = fields.Many2one('budget.category', 'Budget Category', domain="[('company_id', '=', company_id)]")

    @api.constrains('budget_category_id', 'company_id')
    def _check_company(self):
        for line in self:
            if line.budget_category_id and line.budget_category_id.company_id != line.company_id:
                raise ValidationError(_("Company mismatch."))

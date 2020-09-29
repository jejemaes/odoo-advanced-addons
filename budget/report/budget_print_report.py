# -*- coding: utf-8 -*-

import collections
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression

BudgetSection = collections.namedtuple('BudgetSection', 'name total_planned total_practical note')
FakeBudgetCategory = collections.namedtuple('FakeBudgetCategory', 'name color')


class BudgetReport(models.AbstractModel):
    _name = 'report.budget.budget_report_template'
    _description = "Budget Report"

    def _transfert_in_budget_section(self, budget_line):
        return BudgetSection(name=budget_line.budget_category_id.name, total_planned=budget_line.planned_amount, total_practical=budget_line.practical_amount, note=budget_line.description)

    @api.model
    def _get_report_values(self, docids, data=None):
        """
            Returned format:
            {
                budget_id: {
                    'credit': {
                        category1: {seq: 11, total: xxx, subsections: [...]}
                        category2: {seq: 11, total: xxx, subsections: [...]}
                    }
                    'debit': {
                        category1: {seq: 11, total: xxx, subsections: [...]}
                        category2: {seq: 11, total: xxx, subsections: [...]}
                    }
                }
            }
        """
        budget_report = {}

        budgets = self.env['budget.budget'].browse(docids)
        for budget in budgets:

            budget_category_map = {'credit': {}, 'debit': {}}
            for budget_line in budget.budget_line_ids:
                category = budget_line.budget_category_id.parent_id or budget_line.budget_category_id or None

                # debit or credit
                display_mode = False
                if category:
                    display_mode = 'credit' if category.display_type == 'credit' else 'debit'
                else:
                    display_mode = 'credit' if budget_line.planned_amount > 0.0 else 'debit'

                if category not in budget_category_map[display_mode]:
                    budget_category_map[display_mode][category] = {
                        'sequence': budget_line.sequence or 10,
                        'category': category or FakeBudgetCategory(name=_('Uncategorized'), color=0),
                        'total_planned': 0.0,
                        'total_practical': 0.0,
                        'subsections': [],
                    }
                budget_category_map[display_mode][category]['total_planned'] += budget_line.planned_amount
                budget_category_map[display_mode][category]['total_practical'] += budget_line.practical_amount
                budget_category_map[display_mode][category]['subsections'].append(self._transfert_in_budget_section(budget_line))

            budget_report[budget] = budget_category_map

            for display_mode in ['credit', 'debit']:
                budget_section_list = budget_category_map[display_mode].values()
                budget_report[budget][display_mode] = sorted(budget_section_list, key=lambda k: k['sequence'])

        return {
            'doc_ids': docids,
            'doc_model': budgets._name,
            'docs': budgets,
            'budget_report': budget_report,
        }

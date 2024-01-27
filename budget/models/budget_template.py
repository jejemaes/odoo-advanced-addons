# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BudgetTemplate(models.Model):
    _name = 'budget.template'
    _description = "Budget Template"

    name = fields.Char('Name', required=True)
    category_ids = fields.One2many('budget.template.category', 'budget_template_id', 'Categories', copy=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, store=True, default=lambda self: self.env.user.company_id)

    def _prepare_budget_values(self):
        result = {
            'budget_template_id': self.id,
        }
        for fname in self._prepare_budget_value_fields():
            result[fname] = self._fields[fname].convert_to_write(self[fname], self)
        return result

    def _prepare_budget_value_fields(self):
        return ['name', 'company_id']


class BudgetTemplateCategory(models.Model):
    _name = 'budget.template.category'
    _description = "Budget Category"
    _order = 'sequence, name'

    name = fields.Char("Name", required=True)
    color = fields.Integer("Color", default=5)
    budget_template_id = fields.Many2one('budget.template', 'Budget Template', ondelete='cascade', index=True, required=True)
    sequence = fields.Integer("Sequence", default=10)
    company_id = fields.Many2one(related='budget_template_id.company_id', store=True)

    def _create_category(self, budget_id):
        list_value = []
        for category_template in self:
            list_value.append(category_template._prepare_budget_category_values(budget_id))
        return self.env['budget.category'].create(list_value)

    def _prepare_budget_category_values(self, budget_id):
        return {
            'budget_id': budget_id,
            'budget_template_category_id': self.id,
            'name': self.name,
            'color': self.color,
            'sequence': self.sequence,
        }

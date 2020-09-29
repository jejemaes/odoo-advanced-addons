# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Budget(models.Model):
    _name = 'budget.budget'
    _description = "Budget"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Budget Name', required=True, states={'done': [('readonly', True)]}, tracking=True)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    date_from = fields.Date('Start Date', required=True, states={'done': [('readonly', True)]})
    date_to = fields.Date('End Date', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    category_ids = fields.One2many('budget.category', 'budget_id', 'Categories', states={'done': [('readonly', True)]}, copy=True)

    budget_line_ids = fields.One2many('budget.budget.line', 'budget_id', 'Budget Lines', states={'done': [('readonly', True)]}, copy=True)
    planned_credit_amount = fields.Monetary("Total Credit Planned Amount", compute='_compute_planned_amount')
    planned_debit_amount = fields.Monetary("Total Debit Planned Amount", compute='_compute_planned_amount')
    practical_credit_amount = fields.Monetary("Total Credit Practical Amount", compute='_compute_practical_amount')
    practical_debit_amount = fields.Monetary("Total Debit Practical Amount", compute='_compute_practical_amount')

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, store=True, default=lambda self: self.env.user.company_id)

    @api.depends('budget_line_ids.planned_amount')
    def _compute_planned_amount(self):
        for budget in self:
            budget.planned_credit_amount = sum(budget.budget_line_ids.filtered(lambda l: l.planned_amount > 0.0).mapped('planned_amount'))
            budget.planned_debit_amount = sum(budget.budget_line_ids.filtered(lambda l: l.planned_amount < 0.0).mapped('planned_amount'))

    @api.depends('budget_line_ids.practical_amount')
    def _compute_practical_amount(self):
        for budget in self:
            budget.practical_credit_amount = sum(budget.budget_line_ids.filtered(lambda l: l.practical_amount > 0.0).mapped('practical_amount'))
            budget.practical_debit_amount = sum(budget.budget_line_ids.filtered(lambda l: l.practical_amount < 0.0).mapped('practical_amount'))

    def action_budget_confirm(self):
        self.write({'state': 'confirm'})

    def action_budget_draft(self):
        self.write({'state': 'draft'})

    def action_budget_cancel(self):
        self.write({'state': 'cancel'})

    def action_budget_done(self):
        self.write({'state': 'done'})


class BudgetCategory(models.Model):
    _name = 'budget.category'
    _description = "Budget Category"
    _order = 'sequence, name'

    name = fields.Char("Name", required=True)
    color = fields.Integer("Color", default=5)
    budget_id = fields.Many2one('budget.budget', 'Budget', ondelete='cascade', index=True, required=True)
    sequence = fields.Integer("Sequence", default=10)
    company_id = fields.Many2one(related='budget_id.company_id', store=True)


class BudgetLine(models.Model):
    _name = 'budget.budget.line'
    _description = "Budget Line"
    _order = 'budget_id, sequence'

    name = fields.Char("Name", required=True)
    budget_id = fields.Many2one('budget.budget', 'Budget', ondelete='cascade', index=True, required=True)
    budget_state = fields.Selection(related='budget_id.state', string='Budget State', store=True, readonly=True)
    category_id = fields.Many2one('budget.category', "Category", domain="[('budget_id', '=', budget_id)]")
    sequence = fields.Integer("Sequence", default=10)
    description = fields.Text('Note')
    mode = fields.Selection([
        ('manual', 'Manual'),
    ], required=True, default='manual')

    planned_amount = fields.Monetary(
        'Planned Amount', required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    practical_amount = fields.Monetary(
        compute='_compute_practical_amount',
        inverse='_inverse_practical_amount',
        string='Practical Amount',
        help="Amount really earned/spent."
    )
    practical_amount_manual = fields.Monetary("Manual Pratical Amount")
    practical_amount_readonly = fields.Boolean(compute='_compute_practical_amount_readonly')

    percentage = fields.Float(
        compute='_compute_percentage', string='Achievement',
        help="Comparison between practical and theoretical amount. This measure tells you if you are below or over budget.")
    is_above_budget = fields.Boolean(compute='_compute_is_above_budget')
    company_id = fields.Many2one('res.company', related='budget_id.company_id', string='Company', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    @api.depends('mode', 'practical_amount_manual')
    def _compute_practical_amount(self):
        for line in self:
            if line.mode == 'manual':
                line.practical_amount = line.practical_amount_manual or 0.0
            else:
                line.practical_amount = None

    @api.depends('mode')
    def _compute_practical_amount_readonly(self):
        for line in self:
            line.practical_amount_readonly = bool(line.mode != 'manual')

    @api.depends('planned_amount', 'practical_amount')
    def _compute_percentage(self):
        for line in self:
            if line.planned_amount != 0.0:
                line.percentage = float((line.practical_amount or 0.0) / line.planned_amount)
            else:
                line.percentage = 0.0

    @api.depends('planned_amount', 'practical_amount')
    def _compute_is_above_budget(self):
        for line in self:
            if line.planned_amount >= 0:
                line.is_above_budget = line.practical_amount > line.planned_amount
            else:
                line.is_above_budget = line.practical_amount < line.planned_amount

    @api.onchange('practical_amount_manual')
    def _inverse_practical_amount(self):
        for line in self:
            if line.mode == 'manual':
                line.practical_amount_manual = line.practical_amount
            else:
                line.practical_amount_manual = 0.0

    @api.constrains('category_id', 'budget_id')
    def _check_catergory(self):
        for line in self:
            if line.category_id and line.category_id.budget_id != line.budget_id:
                raise ValidationError(_("Budget mismatch."))

    @api.constrains('category_id', 'company_id')
    def _check_company(self):
        for line in self:
            if line.category_id and line.category_id.company_id != line.company_id:
                raise ValidationError(_("Company mismatch."))

    # ------------------------------------------------------------------
    # Business Methods
    # ------------------------------------------------------------------

    def _get_lines_grouped_by_category(self):
        data = {}
        for line in self:
            data.setdefault(line.category_id, self.env['budget.budget.line'])
            data[line.category_id] |= line
        return data

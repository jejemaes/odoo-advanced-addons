# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class BudgetCategory(models.Model):
    _name = 'budget.category'
    _description = "Budget Category"
    _rec_name = 'complete_name'
    _order = 'name'
    _parent_store = True

    name = fields.Char("Name", required=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=False)
    color = fields.Integer("Color")
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id)
    display_type = fields.Selection([
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ], string="Display Type", default='debit', required=True)

    parent_id = fields.Many2one('budget.category', string="Parent", ondelete='cascade')
    parent_path = fields.Char(index=True)
    children_ids = fields.One2many('budget.category', 'parent_id', string="Childrens")
    children_count = fields.Integer("Children Count", compute='_compute_children_count')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.depends('children_ids', 'parent_id')
    def _compute_children_count(self):
        child_data = self.env['budget.category'].read_group([('parent_id', 'in', self.ids)], ['parent_id'], ['parent_id'])
        mapped_data = {m['parent_id'][0]: m['parent_id_count'] for m in child_data}
        for category in self:
            category.children_count = mapped_data.get(category.id, 0)

    @api.onchange('parent_id')
    def _onchange_parent(self):
        if self.parent_id:
            self.display_type = self.parent_id.display_type

    @api.constrains('parent_id', 'children_ids')
    def _check_subcategory_level(self):
        for category in self:
            if category.parent_id and category.children_ids:
                raise ValidationError(_('Category %s cannot have several subcategory levels.' % (category.name,)))

    @api.constrains('parent_id')
    def _check_parent_id(self):
        for category in self:
            if not category._check_recursion():
                raise ValidationError(_('Error! You cannot create recursive hierarchy of category(s).'))

    def write(self, values):
        if values.get('parent_id'):
            category = self.env['budget.category'].browse(values['parent_id'])
            values['display_type'] = category.display_type
        result = super(BudgetCategory, self).write(values)
        if values.get('display_type'):
            super(BudgetCategory, self.mapped('children_ids')).write({'display_type': values['display_type']})
        return result

class BudgetPosition(models.Model):
    _name = 'budget.position'
    _description = "Budgetary Position"
    _order = 'name'

    name = fields.Char('Name', required=True)
    position_type = fields.Selection([
        ('analytic', 'Analytic'),
    ], required=True, default='analytic')
    use_budget_category = fields.Boolean("Use Budget Category", default=False)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id)


class Budget(models.Model):
    _name = 'budget.budget'
    _description = "Budget"
    _inherit = ['mail.thread']

    name = fields.Char('Budget Name', required=True, states={'done': [('readonly', True)]})
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    date_from = fields.Date('Start Date', required=True, states={'done': [('readonly', True)]})
    date_to = fields.Date('End Date', required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'),
        ('done', 'Done')
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False)
    budget_line_ids = fields.One2many('budget.budget.line', 'budget_id', 'Budget Lines', states={'done': [('readonly', True)]}, copy=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id)

    @api.multi
    def action_budget_confirm(self):
        self.write({'state': 'confirm'})

    @api.multi
    def action_budget_draft(self):
        self.write({'state': 'draft'})

    @api.multi
    def action_budget_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_budget_done(self):
        self.write({'state': 'done'})


class BudgetLine(models.Model):
    _name = 'budget.budget.line'
    _description = "Budget Line"
    _order = 'budget_id, sequence, budget_category_id'

    name = fields.Char(compute='_compute_line_name')
    budget_id = fields.Many2one('budget.budget', 'Budget', ondelete='cascade', index=True, required=True)
    budget_state = fields.Selection(related='budget_id.state', string='Budget State', store=True, readonly=True)
    budget_position_id = fields.Many2one('budget.position', 'Budgetary Position', required=True)
    budget_position_type = fields.Selection(related='budget_position_id.position_type')
    budget_category_id = fields.Many2one('budget.category', 'Budget Category')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', index=True)
    sequence = fields.Integer("Sequence", default=10)
    description = fields.Text('Note')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    planned_amount = fields.Monetary(
        'Planned Amount', required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    practical_amount = fields.Monetary(
        compute='_compute_practical_amount', string='Practical Amount', help="Amount really earned/spent.")
    percentage = fields.Float(
        compute='_compute_percentage', string='Achievement',
        help="Comparison between practical and theoretical amount. This measure tells you if you are below or over budget.")
    is_above_budget = fields.Boolean(compute='_compute_is_above_budget')
    company_id = fields.Many2one('res.company', related='budget_id.company_id', string='Company', store=True, readonly=True)

    @api.depends("budget_id", "analytic_account_id")
    def _compute_display_name(self):
        for line in self:
            computed_name = line.budget_id.name
            if line.analytic_account_id:
                computed_name += ' - ' + line.analytic_account_id.name
            line.name = computed_name

    @api.depends('planned_amount', 'practical_amount')
    def _compute_is_above_budget(self):
        for line in self:
            if line.planned_amount >= 0:
                line.is_above_budget = line.practical_amount > line.planned_amount
            else:
                line.is_above_budget = line.practical_amount < line.planned_amount

    @api.depends('planned_amount', 'practical_amount')
    def _compute_percentage(self):
        for line in self:
            if line.planned_amount != 0.0:
                line.percentage = float((line.practical_amount or 0.0) / line.planned_amount)
            else:
                line.percentage = 0.0

    @api.depends('analytic_account_id', 'date_from', 'date_to')
    def _compute_practical_amount(self):
        amount_line_map = {}
        if self.ids:
            lines_with_analytic = self.filtered(lambda line: line.analytic_account_id)
            query = """
                SELECT BL.id AS line_id, SUM(AAL.amount) AS amount, AAL.currency_id AS currency_id, AAL.date AS date
                FROM budget_budget_line BL
                LEFT JOIN account_analytic_account AA ON BL.analytic_account_id = AA.id
                LEFT JOIN account_analytic_line AAL ON AA.id = AAL.account_id
                LEFT JOIN budget_position BP ON BL.budget_position_id = BP.id
                WHERE AAL.date >= BL.date_from
                    AND AAL.date < BL.date_to
                    AND (BP.use_budget_category = 'f' OR (BP.use_budget_category = 't' AND BL.budget_category_id = AAL.budget_category_id))
                    AND BL.id IN %s
                GROUP BY BL.id, AAL.currency_id, AAL.date
            """
            self._cr.execute(query, (tuple(lines_with_analytic.ids),))

            data = self._cr.dictfetchall()
            currency_ids = set([item['currency_id'] for item in data])
            currency_map = {currency.id: currency for currency in self.env['res.currency'].browse(list(currency_ids))}
            budget_lines_map = {line.id: line for line in self}

            amount_line_map = dict.fromkeys(self.ids, 0.0)
            for item in data:
                currency = currency_map[item['currency_id']]
                current_line = budget_lines_map[item['line_id']]

                amount = item['amount']
                if currency != current_line.currency_id:
                    amount = currency._convert(amount, current_line.currency_id, current_line.company_id, item['date'] or fields.Date.today())

                amount_line_map[current_line.id] += amount

        for line in self:
            if line.id in amount_line_map:
                line.practical_amount = amount_line_map[line.id]
            else:
                line.practical_amount = 0.0

    @api.constrains('budget_id', 'date_from', 'date_to')
    def _check_line_dates_between_budget_dates(self):
        for line in self:
            budget_date_from = line.budget_id.date_from
            budget_date_to = line.budget_id.date_to
            if line.date_from:
                date_from = line.date_from
                if date_from < budget_date_from or date_from > budget_date_to:
                    raise ValidationError(_('"Start Date" of the budget line should be included in the Period of the budget'))
            if line.date_to:
                date_to = line.date_to
                if date_to < budget_date_from or date_to > budget_date_to:
                    raise ValidationError(_('"End Date" of the budget line should be included in the Period of the budget'))

    @api.constrains('budget_position_id', 'analytic_account_id')
    def _check_budget_position_configuration(self):
        for line in self:
            if line.budget_position_id.position_type == 'analytic' and not line.analytic_account_id:
                raise ValidationError(_("The analytic account is required as the position is set up in that way."))

    @api.constrains('budget_position_id', 'budget_category_id', 'company_id')
    def _check_company(self):
        for line in self:
            if line.budget_position_id and line.budget_position_id.company_id != line.company_id:
                raise ValidationError(_("Company mismatch."))
            if line.budget_category_id and line.budget_category_id.company_id != line.company_id:
                raise ValidationError(_("Company mismatch."))

    def get_analytic_entry_domain(self):
        result = {}
        for line in self:
            domain = [('account_id', '=', line.analytic_account_id.id), ('date', '>=', line.date_from), ('date', '<=', line.date_to)]
            if line.budget_position_id.use_budget_category:
                domain = expression.AND([domain, [('budget_category_id', '=', line.budget_category_id.id)]])
            result[line.id] = domain
        return result

    def action_view_analytic_entries(self):
        action = self.env['ir.actions.act_window'].for_xml_id('analytic', 'account_analytic_line_action_entries')
        action['domain'] = self.get_analytic_entry_domain()[self.id]

        context = safe_eval(action.get('context', '{}'))
        context['default_budget_category_id'] = self.budget_category_id.id
        context['default_account_id'] = self.analytic_account_id.id
        context['default_date'] = fields.Date.to_string(self.date_from)
        action['context'] = context
        return action

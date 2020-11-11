# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class EventType(models.Model):
    _inherit = 'event.type'

    use_project = fields.Boolean("Organize with a Project", default=False, help="Organize the event with a project and tasks to do.")

    project_start_date_delay = fields.Integer("Project Start Date Delay", default=1)
    project_start_date_unit = fields.Selection([
        ('days', 'Day(s)'),
        ('weeks', 'Week(s)'),
        ('months', 'Month(s)'),
    ], string="Project Start Date Unit", default='days')
    project_start_date_trigger = fields.Selection([
        ('after_event_creation', 'From Event Creation'),
        ('before_event_start', 'Before Event Start Date'),
    ], string="Project Start Date Trigger", default='after_event_creation')

    project_stop_date_delay = fields.Integer("Project Stop Date Delay", default=1)
    project_stop_date_unit = fields.Selection([
        ('days', 'Day(s)'),
        ('weeks', 'Week(s)'),
        ('months', 'Month(s)'),
    ], string="Project Stop Date Unit", default='days')
    project_stop_date_trigger = fields.Selection([
        ('before_event_stop', 'Before Event Stop Date'),
        ('after_event_stop', 'After Event Stop Date'),
    ], string="Project Stop Date Trigger", default='after_event_stop')

    @api.onchange('use_project')
    def _onchange_use_project(self):
        if self.use_project:
            self.use_analytic = True

    @api.constrains('use_analytic', 'use_project')
    def _check_analytic_account(self):
        for event_type in self:
            if event_type.use_project and not event_type.use_project:
                raise ValidationError(_("The event type must activate the analytic account generation, as this account is used to create the project."))

    @api.constrains('use_project', 'project_start_date_delay', 'project_start_date_unit', 'project_start_date_trigger', 'project_stop_date_delay', 'project_stop_date_unit', 'project_stop_date_trigger')
    def _check_use_project_config(self):
        for event_type in self:
            if event_type.use_project:
                for fname in ['project_start_date_delay', 'project_start_date_unit', 'project_start_date_trigger', 'project_stop_date_delay', 'project_stop_date_unit', 'project_stop_date_trigger']:
                    if not event_type[fname]:
                        raise ValidationError(_("As the event template is using project, the period fields to setup begin and end dates of the project must be set."))


class EventEvent(models.Model):
    _inherit = 'event.event'

    project_id = fields.Many2one('project.project', string="Project")

    @api.onchange('analytic_account_id')
    def _onchange_analytic_accound_id_project(self):
        if self.analytic_account_id:
            if self.project_id and self.project_id.analytic_account_id != self.analytic_account_id:
                self.project_id = None
            return {'domain': {'project_id': [('analytic_account_id', '=', self.analytic_account_id.id)]}}
        return {'domain': {'project_id': []}}

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id and not self.analytic_account_id:
            self.analytic_account_id = self.project_id.analytic_account_id

    @api.constrains('project_id', 'analytic_account_id')
    def _check_project_id(self):
        for event in self:
            if event.analytic_account_id and event.project_id:
                if event.analytic_account_id != event.project_id.analytic_account_id:
                    raise ValidationError(_("The project set must share the same analytic account as the one set on the event."))

    @api.model_create_multi
    def create(self, value_list):
        result = super(EventEvent, self).create(value_list)
        result._generate_project()
        return result

    def write(self, values):
        result = super(EventEvent, self).write(values)
        self._generate_project()
        return result

    # ---------------------------------------------------
    #  Actions
    # ---------------------------------------------------

    def action_view_project(self):
        action = self.env.ref('project.act_project_project_2_project_task_all').read()[0]

        eval_context = self.env['ir.actions.actions']._get_eval_context()
        eval_context.update({'active_id': self.project_id.id})

        context = self._context
        if action.get('context'):
            context = safe_eval(action['context'], eval_context)
        action['context'] = context

        domain = []
        if action.get('domain'):
            domain = safe_eval(action['domain'], eval_context)
        action['domain'] = domain

        return action

    # --------------------------------------------------
    # Business
    # --------------------------------------------------

    def _generate_project(self):
        for event in self:
            if event.stage_id.project_required and event.event_type_id.use_project and not event.project_id:
                event._generate_analytic_account(force_create=True)  # force the project to have an analytic account
                values = event._prepare_project_values()
                project = self.env['project.project'].sudo().create(values)
                event.write({'project_id': project.id})

    def _prepare_project_values(self):
        event_type = self.event_type_id

        start_delta = relativedelta(**{event_type.project_start_date_unit: event_type.project_start_date_delay})
        if self.event_type_id.project_start_date_trigger == 'after_event_creation':
            date_start = self.create_date + start_delta
        elif self.event_type_id.project_start_date_trigger == 'before_event_start':
            date_start = self.date_begin - start_delta
        else:
            date_start = fields.Datetime.now()

        end_delta = relativedelta(**{event_type.project_stop_date_unit: event_type.project_stop_date_delay})
        if self.event_type_id.project_stop_date_trigger == 'before_event_stop':
            date_end = self.date_end - end_delta
        elif self.event_type_id.project_stop_date_trigger == 'after_event_stop':
            date_end = self.date_end + end_delta
        else:
            date_end = fields.Datetime.now()

        return {
            'name': self.name,
            'user_id': self.user_id.id,
            'analytic_account_id': self.analytic_account_id.id,
            'date_start': date_start,
            'date': date_end,
            'active': True,
            'company_id': self.company_id.id,
            'description': self.note,
        }


class EventStage(models.Model):
    _inherit = 'event.stage'

    project_required = fields.Boolean("Requires a Project")

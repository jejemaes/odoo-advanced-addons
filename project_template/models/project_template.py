# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    project_template_ids = fields.Many2many('project.template', 'project_template_type_rel', 'type_id', 'project_template_id', string='Project Templates')


class ProjectTemplate(models.Model):
    _name = 'project.template'
    _description = "Project Template"
    _order = 'sequence, id'

    name = fields.Char("Name", required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index')
    user_id = fields.Many2one('res.users', string='Default Project Manager', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Calendar', default=lambda self: self.env.user.company_id.resource_calendar_id.id)

    task_template_ids = fields.One2many('project.task.template', 'project_template_id', string="Task Activities")
    task_template_count = fields.Integer("Task Template Count", compute='_compute_task_template_count')

    stage_shared = fields.Boolean("Share Stages", help="Share stages between projects, or copy them to projects created with this template.")
    stage_ids = fields.Many2many('project.task.type', 'project_template_type_rel', 'project_template_id', 'type_id', string='Tasks Stages')

    privacy_visibility = fields.Selection([
        ('followers', 'Invited employees'),
        ('employees', 'All employees'),
        ('portal', 'Portal users and all employees'),
    ], string='Visibility', required=True, default='portal',
        help="Defines the default visibility of the tasks of the project:\n"
                "- Invited employees: employees may only see the followed project and tasks.\n"
                "- All employees: employees may see all project and tasks.\n"
                "- Portal users and all employees: employees may see everything."
                "   Portal users may see project and tasks followed by.\n"
                "   them or by someone of their company."
    )
    deadline_policy = fields.Selection([
        ('no', "No Deadline"),
        ('before_project_end', "Before Project End Date"),
        ('after_project_begin', "After Project Start Date"),
        ('after_project_creation', "After Project Creation Date"),
    ], string="Deadline Policy", required=True, default='no')

    @api.depends('task_template_ids')
    def _compute_task_template_count(self):
        task_template_data = self.env['project.task.template'].read_group([('project_template_id', 'in', self.ids)], ['project_template_id'], ['project_template_id'])
        result = dict((data['project_template_id'][0], data['project_template_id_count']) for data in task_template_data)

        for template in self:
            template.task_template_count = result.get(template.id, 0)

    def _prepare_project_values(self):
        result = {
            'project_template_id': self.id,
        }
        for fname in self._prepare_project_value_fields():
            result[fname] = self._fields[fname].convert_to_write(self[fname], self)

        stage_ids = []
        for stage in self.stage_ids:
            if not self.stage_shared:
                stage = stage.copy({'project_ids': False, 'project_template_ids': False})
            stage_ids.append(stage.id)
        result['type_ids'] = [(4, stage_id) for stage_id in stage_ids]

        return result

    def _prepare_project_value_fields(self):
        return ['name', 'sequence', 'color', 'user_id', 'company_id', 'resource_calendar_id', 'privacy_visibility']


class ProjectTemplateTask(models.Model):
    _name = 'project.task.template'
    _description = "Project Task Template"
    _order = "sequence, priority, id"

    project_template_id = fields.Many2one('project.template', string='Project Template', required=True)

    name = fields.Char('Title', required=True)
    description = fields.Html(string='Description')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
    ], default='0', string="Priority")
    sequence = fields.Integer(string='Sequence', default=10,
        help="Gives the sequence order when displaying a list of tasks.")
    user_id = fields.Many2one('res.users', string='Default Responsible')
    company_id = fields.Many2one('res.company', related='project_template_id.company_id')
    color = fields.Integer('Color Index')

    tag_ids = fields.Many2many('project.tags', string='Tags')

    deadline_policy = fields.Selection(related='project_template_id.deadline_policy')
    deadline_days = fields.Integer("Deadline Delay (in Days)")
    deadline_hours = fields.Float("Deadline Delay (in Hours)")

    def _create_tasks(self, project_id):
        list_value = []
        for task_template in self:
            list_value.append(task_template._prepare_task_value(project_id))

        return self.env['project.task'].create(list_value)

    def _prepare_task_value(self, project_id):
        project = self.env['project.project'].browse(project_id)

        result = {
            'project_task_template_id': self.id,
            'project_id': project_id,
        }
        for fname in self._prepare_task_value_fields():
            result[fname] = self[fname]

        if self.deadline_policy != 'no' and (self.deadline_hours or self.deadline_days):
            if self.deadline_policy == 'before_project_end':
                deadline = fields.Date.from_string(project.date) - relativedelta(days=self.deadline_days)
            if self.deadline_policy == 'after_project_begin':
                deadline = fields.Date.from_string(project.date_start) + relativedelta(days=self.deadline_days)
            if self.deadline_policy == 'after_project_creation':
                deadline = fields.Datetime.from_string(project.create_date) + relativedelta(days=self.deadline_days, hours=int(self.deadline_hours))
            result['date_deadline'] = fields.Date.to_string(deadline)

        return self.env['project.task']._convert_to_write(result)

    def _prepare_task_value_fields(self):
        return ['name', 'description', 'priority', 'sequence', 'color', 'user_id', 'tag_ids']

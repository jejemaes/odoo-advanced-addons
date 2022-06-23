# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Project(models.Model):
    _inherit = 'project.project'

    project_template_id = fields.Many2one('project.template', string="Template", ondelete='set null')
    project_template_deadline_policy = fields.Selection(related='project_template_id.deadline_policy')

    @api.model_create_multi
    def create(self, list_value):
        template_ids = [item['project_template_id'] for item in list_value if item.get('project_template_id')]
        template_map = {template.id: template for template in self.env['project.template'].browse(template_ids)}

        new_list_value = []
        for values in list_value:
            if values.get('project_template_id'):
                template = template_map[values['project_template_id']]
                template_values = template._prepare_project_values()
                template_values.update(values)
                new_list_value.append(template_values)
            else:
                new_list_value.append(values)

        projects = super(Project, self).create(new_list_value)

        for project in projects:
            if project.project_template_id.task_template_ids:
                project.project_template_id.task_template_ids._create_tasks(project.id)

        return projects


class Task(models.Model):
    _inherit = 'project.task'

    project_task_template_id = fields.Many2one('project.task.template', string='Task Template', readonly=True, ondelete='set null')

# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Stage(models.Model):
    _inherit = 'project.task.type'

    is_closed = fields.Boolean("Is a closing stage")

    def update_date_end(self, stage_id):
        result = super(Stage, self).update_date_end(stage_id)
        # force the correct value since we are in a real closing stage
        project_task_type = self.env['project.task.type'].browse(stage_id)
        if project_task_type.is_closed:
            result['date_end'] = fields.Datetime.now()
        else:
            result['date_end'] = False
        return result


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

    planned_start_date = fields.Date("Planned Start Date", help="Start date for Gantt view")
    planned_stop_date = fields.Date("Planned Stop Date", help="Stop date for Gantt view")

    _sql_constraints = [
        ('planned_dates_chronological', "CHECK(planned_start_date <= planned_stop_date)", 'The planned start date must be smaller than its planned stop date.'),
        ('planned_stop_required', "CHECK((planned_stop_date IS NOT NULL AND planned_start_date IS NOT NULL) OR (planned_stop_date IS NULL))", 'If a task is planned, both start and stop dates are required.'),
    ]

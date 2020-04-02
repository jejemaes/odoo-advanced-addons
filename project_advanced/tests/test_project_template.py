# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.project_advanced.tests.common import TestProjectCommon
from odoo.exceptions import UserError


class TestProjectTemplate(TestProjectCommon):

    def test_create_project_share_stages(self):
        project = self.env['project.project'].create({
            'name': "Test Project",
            'project_template_id': self.template_share.id
        })
        self.assertEqual(set(project.type_ids.ids), set(self.template_share.stage_ids.ids), "Stages must be the same as they are shared")

    def test_create_project_no_share_stages(self):
        project = self.env['project.project'].create({
            'name': "Test Project",
            'project_template_id': self.template_no_share.id
        })
        self.assertNotEqual(set(project.type_ids.ids), set(self.template_share.stage_ids.ids), "Stages should not be the same as they are not shared")

    def test_deadline_no(self):
        project = self.env['project.project'].create({
            'name': "Test Project",
            'project_template_id': self.template_deadline.id,
            'date': '2020-11-03',
        })

        self.assertEqual(len(project.task_ids), len(self.template_deadline.task_template_ids), "Generated tasks count should be the same as the number of task template")
        for task in project.task_ids:
            self.assertFalse(task.date_deadline, "No deadline should be set")

    def test_deadline_before_project_end(self):
        # change the template deadline policy
        self.template_deadline.write({'deadline_policy': 'before_project_end'})

        # create the project
        project = self.env['project.project'].create({
            'name': "Test Project",
            'project_template_id': self.template_deadline.id,
            'date': '2020-11-03',
        })

        self.assertEqual(len(project.task_ids), len(self.template_deadline.task_template_ids), "Generated tasks count should be the same as the number of task template")
        for task in project.task_ids:
            if task.project_task_template_id == self.template_task_1:
                self.assertEqual(task.date_deadline, fields.Date.from_string('2020-11-02'), "Deadline is 1 days before project end (hours ignore)")
            elif task.project_task_template_id == self.template_task_3:
                self.assertEqual(task.date_deadline, fields.Date.from_string('2020-11-01'), "Deadline is 2 days before project end (hours ignore)")
            else:
                self.assertFalse(task.date_deadline, "No deadline should be set since this task template has no deadline delay")

    def test_deadline_after_project_begin(self):
        # change the template deadline policy
        self.template_deadline.write({'deadline_policy': 'after_project_begin'})

        # create the project
        project = self.env['project.project'].create({
            'name': "Test Project",
            'project_template_id': self.template_deadline.id,
            'date_start': '2020-11-03',
        })

        self.assertEqual(len(project.task_ids), len(self.template_deadline.task_template_ids), "Generated tasks count should be the same as the number of task template")
        for task in project.task_ids:
            if task.project_task_template_id == self.template_task_1:
                self.assertEqual(task.date_deadline, fields.Date.from_string('2020-11-04'), "Deadline is 1 days after project start (hours ignore)")
            elif task.project_task_template_id == self.template_task_3:
                self.assertEqual(task.date_deadline, fields.Date.from_string('2020-11-05'), "Deadline is 2 days after project start (hours ignore)")
            else:
                self.assertFalse(task.date_deadline, "No deadline should be set since this task template has no deadline delay")

    def test_deadline_after_project_creation(self):
        # change the template deadline policy
        self.template_deadline.write({'deadline_policy': 'after_project_creation'})

        # create the project
        project = self.env['project.project'].create({
            'name': "Test Project",
            'project_template_id': self.template_deadline.id,
            'date_start': '2020-11-03',
        })

        create_date = project.create_date

        self.assertEqual(len(project.task_ids), len(self.template_deadline.task_template_ids), "Generated tasks count should be the same as the number of task template")
        for task in project.task_ids:
            if task.project_task_template_id == self.template_task_1:
                self.assertEqual(task.date_deadline, (create_date + relativedelta(days=1, hours=3)).date(), "Deadline is 1 days after project start")
            elif task.project_task_template_id == self.template_task_3:
                self.assertEqual(task.date_deadline, (create_date + relativedelta(days=2, hours=5)).date(), "Deadline is 2 days after project start")
            else:
                self.assertFalse(task.date_deadline, "No deadline should be set since this task template has no deadline delay")

# -*- coding: utf-8 -*-

from odoo.tests.common import SavepointCase


class TestProjectCommon(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestProjectCommon, cls).setUpClass()

        # Stages
        cls.type_1 = cls.env['project.task.type'].create({
            'name': 'New',
            'sequence': 1,
        })
        cls.type_2 = cls.env['project.task.type'].create({
            'name': 'In progress',
            'sequence': 2,
        })
        cls.type_3 = cls.env['project.task.type'].create({
            'name': 'Done',
            'sequence': 3,
            'is_closed': True,
        })

        # Templates
        cls.template_no_share = cls.env['project.template'].create({
            'name': 'My Template',
            'privacy_visibility': 'employees',
            'sequence': 5,
            'stage_shared': False,
            'stage_ids': [(6, 0, [cls.type_1.id, cls.type_2.id, cls.type_3.id])],
            'deadline_policy': 'no',
        })
        cls.template_share = cls.env['project.template'].create({
            'name': 'My Template, share stages',
            'privacy_visibility': 'employees',
            'sequence': 5,
            'stage_shared': True,
            'stage_ids': [(6, 0, [cls.type_1.id, cls.type_2.id, cls.type_3.id])],
            'deadline_policy': 'no',
        })
        cls.template_deadline = cls.env['project.template'].create({
            'name': 'My Template, deadline',
            'privacy_visibility': 'employees',
            'sequence': 5,
            'stage_shared': True,
            'stage_ids': [(6, 0, [cls.type_1.id, cls.type_2.id, cls.type_3.id])],
            'deadline_policy': 'no',
        })

        # Task template
        cls.template_task_1 = cls.env['project.task.template'].create({
            'name': 'Task 1 in template deadline',
            'priority': '0',
            'project_template_id': cls.template_deadline.id,
            'deadline_days': 1,
            'deadline_hours': 3,
        })
        cls.template_task_2 = cls.env['project.task.template'].create({
            'name': 'Task 2 in template deadline',
            'priority': '1',
            'project_template_id': cls.template_deadline.id
        })
        cls.template_task_3 = cls.env['project.task.template'].create({
            'name': 'Task 3 in template deadline',
            'priority': '0',
            'project_template_id': cls.template_deadline.id,
            'deadline_days': 2,
            'deadline_hours': 5,
        })
        cls.template_task_4 = cls.env['project.task.template'].create({
            'name': 'Task 4 in template deadline',
            'priority': '1',
            'project_template_id': cls.template_deadline.id
        })

# -*- coding: utf-8 -*-

from odoo import fields, models


class Task(models.Model):
    _inherit = 'project.task'

    event_id = fields.Many2one('event.event', string="Event")

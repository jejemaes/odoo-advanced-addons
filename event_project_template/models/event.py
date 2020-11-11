# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class EventType(models.Model):
    _inherit = 'event.type'

    project_template_id = fields.Many2one('project.template', string="Project Template")


class EventEvent(models.Model):
    _inherit = 'event.event'

    def _prepare_project_values(self):
        result = super(EventEvent, self)._prepare_project_values()
        if self.event_type_id.project_template_id:
            result['project_template_id'] = self.event_type_id.project_template_id.id
        return result

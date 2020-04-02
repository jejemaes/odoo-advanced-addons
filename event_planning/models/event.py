# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class EventType(models.Model):
    _inherit = 'event.type'

    use_planning = fields.Boolean("Organize with a Planning", default=False, help="Organize the planning event.")


class EventEvent(models.Model):
    _inherit = 'event.event'

    planning_id = fields.Many2one('planning.planning', string="Planning")
    planning_date_start = fields.Datetime("Planning Start Date", related='planning_id.date_start', readonly=False)
    planning_date_stop = fields.Datetime("Planning Stop Date", related='planning_id.date_stop', readonly=False)

    @api.model_create_multi
    def create(self, value_list):
        result = super(EventEvent, self).create(value_list)
        result.filtered(lambda event: event.event_type_id.use_planning)._generate_planning()
        return result

    def write(self, values):
        result = super(EventEvent, self).write(values)
        self.filtered(lambda event: event.event_type_id.use_planning)._generate_planning()
        return result

    # ---------------------------------------------------
    #  Actions
    # ---------------------------------------------------

    def action_view_planning(self):
        action = self.planning_id.action_view_shifts()

        # change context by adding event info
        context = action.get('context', dict(self._context))
        context['default_event_id'] = self.id
        context['default_date_from'] = fields.Datetime.to_string(self.date_begin)
        action['context'] = context
        return action

    def action_generate_planning(self):
        self._generate_planning(force_create=True)
        return True

    # --------------------------------------------------
    # Business
    # --------------------------------------------------

    def _generate_planning(self, force_create=False):
        plannings = self.env['planning.planning']
        for event in self:
            if not event.planning_id or force_create:
                values = event._prepare_planning_values()
                planning = self.env['planning.planning'].sudo().create(values)
                event.write({'planning_id': planning.id})
                plannings |= planning
        return plannings

    def _prepare_planning_values(self):
        return {
            'name': self.name,
            'user_id': self.user_id.id,
            'date_start': self.date_begin,
            'date_stop': self.date_end,
            'company_id': self.company_id.id,
            'include_open_shift': True,
            'planning_type': 'event',
            'event_id': self.id,
        }

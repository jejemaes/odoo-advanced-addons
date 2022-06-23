# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class PlanningShift(models.Model):
    _inherit = 'planning.shift'

    event_id = fields.Many2one('event.event', string="Event")


class PlanningPlanning(models.Model):
    _inherit = 'planning.planning'

    event_id = fields.Many2one('event.event', string="Event")
    planning_type = fields.Selection(selection_add=[('event', 'Event')], ondelete={'event': 'set default'})

    _sql_constraints = [
        ('event_required', "CHECK((planning_type = 'event' AND event_id IS NOT NULL) OR (planning_type != 'event'))", 'The event is required for planning of event.'),
    ]

    @api.onchange('planning_type')
    def _onchange_planning_type_event(self):
        if self.planning_type != 'event':
            self.event_id = None

    def get_shift_domain(self):
        domain = super().get_shift_domain()
        if self.planning_type == 'event':
            domain = expression.AND([domain, [('event_id', '=', self.event_id.id)]])
        return domain

    def action_view_shifts(self):
        action = super().action_view_shifts()
        if self.event_id:
            # change context by adding event info
            context = action.get('context', dict(self._context))
            context['default_event_id'] = self.event_id.id
            context['default_date_from'] = fields.Datetime.to_string(self.date_start)

            action['context'] = context
        return action

    def get_planning_data_for_shift(self):
        values = super().get_planning_data_for_shift()
        if self.planning_type == 'event':
            values['event_id'] = self.event_id.id
        return values

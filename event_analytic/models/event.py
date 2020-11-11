# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventType(models.Model):
    _inherit = 'event.type'

    use_analytic = fields.Boolean("Track Costs", default=False, help="Track costs with an analytic account")
    analytic_group_id = fields.Many2one('account.analytic.group', string="Analytic Category", help="Generate a analytic account on event creation with this category.")


class EventEvent(models.Model):
    _inherit = 'event.event'

    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")

    @api.model_create_multi
    def create(self, value_list):
        result = super(EventEvent, self).create(value_list)
        result._generate_analytic_account()
        return result

    def write(self, values):
        result = super(EventEvent, self).write(values)
        self._generate_analytic_account()
        return result

    # ---------------------------------------------------
    #  Business Methods
    # ---------------------------------------------------

    def _generate_analytic_account(self, force_create=False):
        for event in self:
            if force_create or (event.stage_id.analytic_account_required and event.event_type_id.use_analytic):
                if not event.analytic_account_id:
                    analytic_values = event._prepare_analytic_account_values()
                    account_analytic = self.env['account.analytic.account'].sudo().create(analytic_values)
                    event.write({'analytic_account_id': account_analytic.id})

    def _prepare_analytic_account_values(self):
        return {
            'name': self.name,
            'group_id': self.event_type_id.analytic_group_id.id,
            'partner_id': self.organizer_id.id,
            'company_id': self.company_id.id,
            'active': True,
        }


class EventStage(models.Model):
    _inherit = 'event.stage'

    analytic_account_required = fields.Boolean("Requires an Analytic Account")

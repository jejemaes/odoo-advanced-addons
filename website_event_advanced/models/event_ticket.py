# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventTicketType(models.Model):
    _inherit = 'event.type.ticket'

    seats_registration_limit = fields.Integer("Limit Seats Registration", help="""This limits the number of seats a user can register on the website.""")

    @api.model
    def _get_event_ticket_fields_whitelist(self):
        return super()._get_event_ticket_fields_whitelist() + ['seats_registration_limit']


class EventTicket(models.Model):
    _inherit = 'event.event.ticket'

    seats_registration_limit = fields.Integer("Limit Seats Registration", help="""This limits the number of seats a user can register on the website.""")

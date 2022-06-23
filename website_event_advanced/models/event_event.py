# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import slug


class EventEvent(models.Model):
    _inherit = 'event.event'

    registration_phone_mandatory = fields.Boolean("Phone Mandatory on Registration", compute='_compute_registration_phone_mandatory', store=True, readonly=False)
    website_hide_event_location = fields.Boolean("Hide Event Location", compute='_compute_website_hide_event_location', store=True, readonly=False, help="Hide Event Location on Event website page.")

    @api.onchange('use_registration')
    def _onchange_use_registration(self):
        if not self.use_registration:
            self.menu_register_cta = False

    @api.depends('use_registration')
    def _compute_menu_register_cta(self):
        super(EventEvent, self)._compute_menu_register_cta()
        for event in self:
            if not event.use_registration:
                event.menu_register_cta = False

    @api.depends('event_type_id')
    def _compute_registration_phone_mandatory(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Purpose is to emulate an
        onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method. """
        for event in self:
            if not event.event_type_id:
                event.registration_phone_mandatory = event.registration_phone_mandatory or False
            else:
                event.registration_phone_mandatory = event.event_type_id.registration_phone_mandatory or False

    @api.depends('event_type_id')
    def _compute_website_hide_event_location(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Purpose is to emulate an
        onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method. """
        for event in self:
            if not event.event_type_id:
                event.website_hide_event_location = event.website_hide_event_location or False
            else:
                event.website_hide_event_location = event.event_type_id.website_hide_event_location or False

    def _get_website_menu_entries(self):
        result = super(EventEvent, self)._get_website_menu_entries()
        if not self.use_registration:
            result = result[:-1]
            result.append((_('Details'), '/event/%s/register' % slug(self), False, 100, False),)
        return result

# -*- coding: utf-8 -*-

from odoo import api, fields, models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    def _get_website_registration_allowed_fields(self):
        fields = super()._get_website_registration_allowed_fields()
        fields.add("qty")
        return fields

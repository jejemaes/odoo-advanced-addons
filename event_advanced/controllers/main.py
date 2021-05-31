# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request


class EventQRCode(http.Controller):

    @http.route(['/event/<model("event.event"):event>/<string:registration_token>'], type='http', auth="user")
    def event_registrer_qrcode(self, event, registration_token):
        registration = request.env['event.registration'].search([('access_token', '=', registration_token)], limit=1)
        values = {
            'event': event,
            'mode': 'invalid_ticket',
            'registration': registration,
        }
        if registration:
            if registration.state == 'cancel':
                values['mode'] = 'canceled_registration'
            elif not registration.event_id.is_ongoing:
                values['mode'] = 'not_ongoing_event'
            elif registration.state != 'done':
                if registration.event_id != event:
                    values['mode'] = 'need_manual_confirmation'
                else:
                    registration.action_set_done()
                    values['mode'] = 'confirmed_registration'
            else:
                values['mode'] = 'already_registered'
        return request.render('event_advanced.page_registration_qrcode', values)

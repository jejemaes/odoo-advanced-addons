# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request

from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEventAdvancedController(WebsiteEventController):

    # ----------------------------------------------------------
    # Quantity on Registration
    # ----------------------------------------------------------

    def _process_tickets_form(self, event, form_details):
        """ Process posted data about ticket order. Generic ticket are supported
        for event without tickets (generic registration).

        :return: list of order per ticket: [{
            'id': if of ticket if any (0 if no ticket),
            'ticket': browse record of ticket if any (None if no ticket),
            'name': ticket name (or generic 'Registration' name if no ticket),
            'quantity': number of registrations for that ticket,
        }, {...}]
        """
        result = super()._process_tickets_form(event, form_details)

        if event.registration_multi_qty:
            for value in result:
                value['registration_qty'] = value['quantity']
                value['quantity'] = 1

        return result



    def _process_attendees_form(self, event, form_details):
        print('form_details',form_details)
        result = super()._process_attendees_form(event, form_details)
        print('================_process_attendees_form', result)
        return result

    def _create_attendees_from_registration_post(self, event, registration_data):
        print('registration_data',registration_data)
        result = super()._create_attendees_from_registration_post(event, registration_data)
        print('================_create_attendees_from_registration_post', result)
        return result

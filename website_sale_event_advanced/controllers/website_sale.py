# -*- coding: utf-8 -*-

import logging

from odoo import fields, _
from odoo.addons.website_event_sale.controllers.main import WebsiteEventSaleController
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsiteEventAdvancedSaleController(WebsiteEventSaleController):

    def _create_attendees_from_registration_post(self, event, registration_data):
        # copy of original values to keep the quantity
        registration_data_initial = [dict(item) for item in registration_data]

        # super() resets the quantity to 1 on SO line and registration !!
        registrations = super(WebsiteEventAdvancedSaleController, self)._create_attendees_from_registration_post(event, registration_data)

        order = request.website.sale_get_order(force_create=False)
        if order:

            # set the quantity on the SO line created by super().
            if event.registration_multi_qty:
                for registration, registration_values in zip(registrations, [r for r in registration_data_initial if r.get('event_ticket_id')]):
                    registration.qty = registration_values.get('qty')
                    if registration.sale_order_line_id and registration.qty:
                        order.with_context(event_ticket_id=registration.event_ticket_id.id, fixed_price=True)._cart_update(
                            product_id=registration.sale_order_line_id.product_id.id,
                            line_id=registration.sale_order_line_id.id,
                            set_qty=registration.qty
                        )

            # delete SO line of pre-order event ticket
            so_line_to_remove = request.env['sale.order.line']
            for registration in registrations:
                if registration.event_ticket_id.online_pre_order:
                    so_line_to_remove |= registration.sale_order_line_id
                    registration.sale_order_line_id = None
                    registration.sale_order_id = None

            so_line_to_remove.sudo().unlink()

            if len(order.order_line) == 0:
                order.unlink()
                request.website.sale_reset()

        return registrations

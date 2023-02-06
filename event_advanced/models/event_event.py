# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EventEvent(models.Model):
    _inherit = 'event.event'

    use_qrcode = fields.Boolean("Use QRCode on Registration", compute='_compute_use_qrcode', default=False, readonly=False, store=True)
    use_registration = fields.Boolean("Allow Registration", compute='_compute_use_registration', default=True, readonly=False, store=True, help="Check this to allow people to register to the event and activate the attendees management")
    registration_multi_qty = fields.Boolean("Allow Quantity on Registration", compute='_compute_registration_multi_qty', readonly=False, store=True, help="Allow multiple attendee on one registration (instead of one registration per customer).")

    @api.depends('event_type_id')
    def _compute_use_qrcode(self):
        for event in self:
            event.use_qrcode = event.event_type_id.use_qrcode

    @api.depends('event_type_id')
    def _compute_use_registration(self):
        for event in self:
            event.use_registration = event.event_type_id.use_registration

    @api.depends('event_type_id')
    def _compute_registration_multi_qty(self):
        for event in self:
            event.registration_multi_qty = event.event_type_id.registration_multi_qty

    @api.depends("seats_max", "registration_ids.state", "registration_ids.qty")
    def _compute_seats(self):
        multi_qty_events = self.filtered("registration_multi_qty")
        for event in multi_qty_events:
            vals = {
                "seats_unconfirmed": 0,
                "seats_reserved": 0,
                "seats_used": 0,
                "seats_available": 0,
            }
            registrations = self.env["event.registration"].read_group(
                [
                    ("event_id", "=", event.id),
                    ("state", "in", ["draft", "open", "done"]),
                ],
                ["state", "qty"],
                ["state"],
            )
            for registration in registrations:
                if registration["state"] == "draft":
                    vals["seats_unconfirmed"] += registration["qty"]
                elif registration["state"] == "open":
                    vals["seats_reserved"] += registration["qty"]
                elif registration["state"] == "done":
                    vals["seats_used"] += registration["qty"]
            if event.seats_max > 0:
                vals["seats_available"] = event.seats_max - (
                    vals["seats_reserved"] + vals["seats_used"]
                )
            vals["seats_expected"] = (
                vals["seats_unconfirmed"] + vals["seats_reserved"] + vals["seats_used"]
            )
            event.update(vals)
        rest = self - multi_qty_events
        super(EventEvent, rest)._compute_seats()

    @api.onchange('use_registration')
    def _onchange_use_registration(self):
        if not self.use_registration:
            self.use_qrcode = False
            self.seats_limited = False
            self.auto_confirm = False
            self.registration_multi_qty = False

    @api.constrains("registration_multi_qty")
    def _check_attendees_qty(self):
        for event in self:
            if (
                not event.registration_multi_qty
                and max(event.registration_ids.mapped("qty") or [0]) > 1
            ):
                raise ValidationError(
                    _(
                        "You can not disable this option if there are "
                        "registrations with quantities greater than one."
                    )
                )

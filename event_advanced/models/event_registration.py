# -*- coding: utf-8 -*-

import base64
import io
import logging
import qrcode
import uuid

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    def _default_access_token(self):
        return str(uuid.uuid4())

    access_token = fields.Char(default=_default_access_token, readonly=True, copy=False, index=True)
    qrcode_url = fields.Char("Url", compute='_compute_qrcode_url')
    qrcode = fields.Binary("QR Code", compute='_compute_qrcode', attachment=False, store=False, readonly=True)

    event_registration_multi_qty = fields.Boolean(related='event_id.registration_multi_qty', readonly=True)
    qty = fields.Integer(
        string="Quantity",
        required=True,
        default=1,
    )

    _sql_constraints = [
        ('access_token_event_uniq', 'unique(access_token)', "access_token should be unique")
    ]

    @api.depends('event_id.use_qrcode')
    def _compute_qrcode_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for registration in self:
            if registration.id:
                if registration.event_id.use_qrcode:
                    registration.qrcode_url = '%s/event/%s/%s' % (base_url, slug(registration.event_id), registration.access_token,)
                else:
                    registration.qrcode_url = False
            else:
                registration.qrcode_url = False

    @api.depends('qrcode_url')
    def _compute_qrcode(self):
        for registration in self:
            url = registration.qrcode_url
            if url:
                data = io.BytesIO()
                qrcode.make(url.encode(), box_size=12, version=3).save(data, optimise=True, format='PNG')
                registration.qrcode = base64.b64encode(data.getvalue()).decode()
            else:
                registration.qrcode = False

    def _init_column(self, column_name):
        """ Populate the acces_token column for existing records """
        if column_name == "access_token":
            _logger.debug("Table '%s': setting default value of new column %s to unique values for each row",
                          self._table, column_name)
            self.env.cr.execute("SELECT id FROM %s WHERE access_token IS NULL" % self._table)
            registration_ids = self.env.cr.dictfetchall()
            query_list = [{'id': reg['id'], 'access_token': self._default_access_token()} for reg in registration_ids]
            query = 'UPDATE ' + self._table + ' SET access_token = %(access_token)s WHERE id = %(id)s;'
            self.env.cr._obj.executemany(query, query_list)
        else:
            super(EventRegistration, self)._init_column(column_name)

    @api.constrains("qty")
    def _check_attendees_qty(self):
        for registration in self:
            if (
                not registration.event_registration_multi_qty
                and registration.qty > 1
            ):
                raise ValidationError(
                    _("You can not add quantities if you not active the option. Allow multiple attendees per registration in event")
                )

    @api.model
    def register_attendee(self, access_token, event_id):
        attendee = self.search([('access_token', '=', access_token)], limit=1)
        if not attendee:
            return {'error': 'invalid_ticket'}
        res = attendee._get_registration_summary()
        if attendee.state == 'cancel':
            status = 'canceled_registration'
        elif not attendee.event_id.is_ongoing:
            status = 'not_ongoing_event'
        elif attendee.state != 'done':
            if event_id and attendee.event_id.id != event_id:
                status = 'need_manual_confirmation'
            else:
                attendee.action_set_done()
                status = 'confirmed_registration'
        else:
            status = 'already_registered'
        res.update({'status': status, 'event_id': event_id})
        return res

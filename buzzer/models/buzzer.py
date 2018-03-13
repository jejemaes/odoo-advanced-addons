# -*- coding: utf-8 -*-
from datetime import datetime
import uuid

from odoo import api, fields, models


class BuzzChannel(models.Model):

    _name = 'buzzer.channel'
    _description = "Buzzer Channel"

    name = fields.Char("Name", required=True)
    description = fields.Text("Description")
    uuid = fields.Char('UUID', size=50, index=True, default=lambda self: '%s' % uuid.uuid4())
    user_id = fields.Many2one('res.users', 'Current Responsible', readonly=False)
    user_ids = fields.Many2many('res.users', 'buzzer_res_users', 'buzz_channel_id', 'user_id', 'Participant Users')
    is_responsible = fields.Boolean("Am I responsible", compute='_compute_is_responsible')
    url = fields.Char("Url", compute='_compute_url')

    @api.multi
    def _compute_url(self):
        for channel in self:
            channel.url = '/buzzer/%s' % (channel.id,)

    @api.multi
    def _compute_is_responsible(self):
        for channel in self:
            channel.is_responsible = self.env.user == channel.user_id

    # -----------------------------------------
    # Actions
    # -----------------------------------------

    def action_buzzer_panel(self):
        self.write({'user_id': self.env.user.id})
        self.buzz_assignation()
        action = self.env.ref('buzzer.buzzer_channel_action_client').read()[0]
        action['params'] = {
            'channel_uuid': self.uuid,
            'channel_id': self.id,
        }
        return action

    def action_reset_responsible(self, redirect=False):
        self.write({'user_id': False})
        return False

    # -----------------------------------------
    # Bus Notifications
    # -----------------------------------------

    def buzz(self):
        notifications = []
        for channel in self:
            buzz_time = str(datetime.now())
            payload = {
                '_type': 'buzzer',
                'action': 'buzz',
                'channel_id': channel.id,
                'channel_uuid': channel.uuid,
                'time': buzz_time,
                'user_id': self.env.user.id,
            }
            notifications.append([(self._cr.dbname, 'buzzer.channel', channel.id), payload])
            notifications.append([channel.uuid, payload])
        return self.env['bus.bus'].sendmany(notifications)

    def buzz_reset(self):
        notifications = []
        for channel in self:
            payload = {
                '_type': 'buzzer',
                'action': 'reset',
                'channel_id': channel.id,
                'channel_uuid': channel.uuid,
                'user_id': self.env.user.id,
            }
            notifications.append([(self._cr.dbname, 'buzzer.channel', channel.id), payload])
            notifications.append([channel.uuid, payload])
        return self.env['bus.bus'].sendmany(notifications)

    def buzz_assignation(self):
        notifications = []
        for channel in self:
            payload = {
                '_type': 'buzzer',
                'action': 'assigned',
            }
            notifications.append([(self._cr.dbname, 'buzzer.channel', channel.id), payload])
            notifications.append([channel.uuid, payload])
        return self.env['bus.bus'].sendmany(notifications)

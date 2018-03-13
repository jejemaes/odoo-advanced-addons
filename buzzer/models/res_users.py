# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Users(models.Model):

    _inherit = 'res.users'

    buzzer_channel_ids = fields.Many2many('buzzer.channel', 'buzzer_res_users', 'user_id', 'buzz_channel_id', 'Buzzer Channels')

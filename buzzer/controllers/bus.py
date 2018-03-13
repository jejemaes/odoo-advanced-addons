# -*- coding: utf-8 -*

from odoo.addons.bus.controllers.main import BusController
from odoo.http import request


class BuzzerBusController(BusController):

    # --------------------------
    # Extends BUS Controller Poll
    # --------------------------
    def _poll(self, dbname, channels, last, options):
        channels = list(channels)
        if request.session.uid:
            for buzzer_channel in request.env['buzzer.channel'].search([('user_ids', 'in', [request.env.user.id])]):
                channels.append((request.db, 'buzzer.channel', buzzer_channel.id))
        if request.env.user.has_group('base.group_user'):
            for buzzer_channel in request.env['buzzer.channel'].search([('user_id', '=', request.env.user.id)]):
                channels.append(buzzer_channel.uuid)

        return super(BuzzerBusController, self)._poll(dbname, channels, last, options)

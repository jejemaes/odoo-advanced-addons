# -*- coding: utf-8 -*

from odoo.http import request
from odoo import http


class BuzzerController(http.Controller):

    @http.route('/buzzer', type='http', auth="user")
    def buzzer_index(self):
        channels = request.env['buzzer.channel'].search([('user_ids', 'in', [request.env.user.id]), ('user_id', '!=', False)])
        return request.render('buzzer.buzzer_index_page', {
            'channels': channels,
        })

    @http.route('/buzzer/<model("buzzer.channel"):channel>', type='http', auth="user")
    def buzzer_page_buzz(self, channel, **kwargs):
        return request.render('buzzer.buzzer_buzz_page', {
            'channel': channel,
            'user': request.env.user,
        })

    @http.route('/buzzer/<string:channel_uuid>/buzz', type='json', auth="user")
    def buzzer_action_buzz(self, channel_uuid):
        channel = request.env['buzzer.channel'].search([('uuid', '=', channel_uuid)], limit=1)
        return channel.buzz()

    @http.route('/buzzer/client_action', type='json', auth="user")
    def buzzer_action_client(self, channel_id):
        channel = request.env['buzzer.channel'].browse(channel_id)
        return {
            'channel': channel.read([])[0],
            'participants': channel.user_ids.read(['login', 'im_status'])
        }

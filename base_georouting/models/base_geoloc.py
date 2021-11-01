# -*- coding: utf-8 -*-

import requests
import logging

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class GeoProvider(models.Model):
    _inherit = "base.geo_provider"

    routing_use_address = fields.Boolean("Computing route use address", default=False, help="Use string address or lat/long of the partner to compute distance between 2 partners.")
    routing_choice_policy = fields.Selection([('first', 'First one')], string="Routing Choice Policy", help="If several route, define the policy to choice one.", default='first', required=True)

    @api.model
    def get_provider(self):
        prov_id = self.env['ir.config_parameter'].sudo().get_param('base_geolocalize.geo_provider')
        if prov_id:
            provider = self.env['base.geo_provider'].browse(int(prov_id))
        if not prov_id or not provider.exists():
            provider = self.env['base.geo_provider'].search([], limit=1)
        return provider

    def calculate_route_distance(self, partner_src, partner_dst):
        """ Return the distance using a route calculation in meter between 2 partners """
        method_name = '_%s_calculate_routes' % (self.tech_name,)
        if hasattr(self, method_name):
            if self.routing_use_address:
                address_src = self.env['geo.coder'].geo_query_address(street=partner_src.street, zip=partner_src.zip, city=partner_src.city, state=partner_src.state_id.name, country=partner_src.country_id.name)
                address_dst = self.env['geo.coder'].geo_query_address(street=partner_dst.street, zip=partner_dst.zip, city=partner_dst.city, state=partner_dst.state_id.name, country=partner_dst.country_id.name)
                return getattr(self, method_name)(address_src, address_dst)
            else:
                partner_src.ensure_geolocalization()
                partner_dst.ensure_geolocalization()
                coord_src = (partner_src.partner_latitude, partner_src.partner_longitude)
                coord_dst = (partner_dst.partner_latitude, partner_dst.partner_longitude)
                return getattr(self, method_name)(coord_src, coord_dst)
        return None

    def _openstreetmap_calculate_routes(self, coord_src, coord_dst):
        """ Response from openstreetmap (https://github.com/Project-OSRM/osrm-backend/blob/master/docs/http.md#route-service):
            {
                "code": "Ok",
                "waypoints": [{
                    "hint": "Eo_6iIaP-ogYAAAABQAAAAAAAAAgAAAASjFaQdLNK0AAAAAAsPePQQwAAAADAAAAAAAAABAAAAAz5QAA_kvMAKlYIQM8TMwArVghAwAA7wp1Zh4C",
                    "distance": 4.231666,
                    "location": [13.388798, 52.517033],
                    "name": "Friedrichstraße"
                }, {
                    "hint": "X2cigI7v64gGAAAACgAAAAAAAAB2AAAAW7-PQOKcyEAAAAAApq6DQgYAAAAKAAAAAAAAAHYAAAAz5QAAf27MABiJIQOCbswA_4ghAwAAXwV1Zh4C",
                    "distance": 2.789393,
                    "location": [13.397631, 52.529432],
                    "name": "Torstraße"
                }],
                "routes": [{
                    "legs": [{
                        "steps": [],
                        "weight": 252.7,
                        "distance": 1884.7,
                        "summary": "",
                        "duration": 251.5
                    }],
                    "weight_name": "routability",
                    "weight": 252.7,
                    "distance": 1884.7,
                    "duration": 251.5
                }]
            }

            Distance is in meter !
        """
        url = 'https://routing.openstreetmap.de/routed-car/route/v1/driving/%s,%s;%s,%s?overview=false&alternatives=true&steps=true' % (coord_src[1], coord_src[0], coord_dst[1], coord_dst[0])
        _logger.info('Geo routing computes distance with %s', url)
        response = requests.get(url)
        if response.status_code != 200:
            _logger.error('Request to openstreetmap route API failed.\nCode: %s\nContent: %s' % (response.status_code, response.content))
            return None

        response_data = response.json()

        if "routes" in response_data:
            if len(response_data['routes']) == 0:
                return None
            if len(response_data['routes']) == 1:
                return response_data['routes'][0].get('distance', 0.0)
            distance_meter = self._openstreetmap_apply_routing_policy(response_data)
            return distance_meter
        return None

    def _openstreetmap_apply_routing_policy(self, response_data):
        if self.routing_choice_policy == 'first':
            return response_data['routes'][0].get('distance', 0.0)
        return None

    def _googlemap_calculate_routes(self, coord_src, coord_dst):
        pass

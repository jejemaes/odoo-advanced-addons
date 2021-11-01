# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def write(self, values):
        if any(fname in ['street', 'street2', 'zip', 'city', 'state_id', 'country_id'] for fname in values):
            values['partner_latitude'] = None
            values['partner_longitude'] = None
        return super().write(values)

    @api.model
    def _geo_localize_route(self, street='', zip='', city='', state='', country=''):
        """ This method does not approximate the localization: it requires at least a city or zip
            to be set. This does not fallback on only the country.
            Should be used to geolocalize more precisly partners (when changing their address, ....)
        """
        geo_obj = self.env['base.geocoder']
        search = geo_obj.geo_query_address(street=street, zip=zip, city=city, state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)
        return result

    def ensure_geolocalization(self):
        for partner in self:
            if not partner.partner_latitude or not partner.partner_latitude:
                partner.geo_localize()

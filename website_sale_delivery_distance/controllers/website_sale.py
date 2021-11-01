# -*- coding: utf-8 -*-

from odoo import fields, _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteShop(WebsiteSale):

    def values_postprocess(self, order, mode, values, errors, error_msg):
        new_values, errors, error_msg = super(WebsiteShop, self).values_postprocess(order, mode, values, errors, error_msg)

        # check if address field are filled with whitespace
        wrong_address = False
        shipping_fields_required = self._get_mandatory_fields_shipping(order.partner_shipping_id.country_id.id)
        for fname in shipping_fields_required:
            if not str(values.get(fname, '')).strip():  # avoid spaces as address part (odoo shop allows it !)
                wrong_address = True
                if not fname in errors:
                    errors[fname] = 'error'
        if wrong_address:
            error_msg.append(_("Some address parts are filled with spaces or whitespaces. We need a complete address to localize you."))

        # if not errors on the address fields, try to locate it
        if not any(fname in errors for fname in shipping_fields_required):
            # compute the lat / long of the partner
            state_name = request.env['res.country.state'].browse(new_values['state_id']).name if new_values.get('state_id') else ''
            country_name = request.env['res.country'].browse(new_values['country_id']).name if new_values.get('country_id') else ''
            result = request.env['res.partner'].sudo()._geo_localize_route(street=new_values.get('street', ''), zip=new_values.get('zip', ''), city=new_values.get('city', ''), state=state_name, country=country_name)
            # if can not be locate, then don't create and return errors
            if result is None:
                error_msg.append(_("Can not locate the given address. Please be carreful and be precise; don't forget the number in the street, check the spell of street name, ..."))
                for fname in shipping_fields_required:
                    if not fname in errors:
                        errors[fname] = 'error'
            # otherwise, extend the new_values (lat / long / date_localisation)
            else:
                new_values['partner_latitude'] = result[0]
                new_values['partner_longitude'] = result[1]
                new_values['date_localization'] = fields.Date.context_today(order)

        return new_values, errors, error_msg

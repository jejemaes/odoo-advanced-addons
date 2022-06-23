# -*- coding: utf-8 -*-

from itertools import chain
from pytz import utc


import math
from datetime import datetime, time, timedelta
from dateutil.rrule import rrule, DAILY
from functools import partial
from itertools import chain
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round

from odoo import api, fields, models, _
from odoo.addons.resource.models.resource import Intervals


class Resource(models.Model):
    _inherit = 'resource.resource'

    product_template_id = fields.Many2one('product.template', 'Product Template', domain=[('can_be_rented', '=', True), ('rental_tracking', '=', 'use_resource')])
    product_id = fields.Many2one('product.product', 'Product', domain="[('can_be_rented', '=', True), ('product_tmpl_id', '=', product_template_id), ('rental_tracking', '=', 'use_resource')]")

    @api.onchange('product_template_id')
    def _onchange_product_template_id(self):
        if not self.product_template_id:
            self.product_id = False
        else:
            self.product_id = self.product_template_id.product_variant_id

    @api.constrains('product_template_id', 'product_id')
    def _check_product_id_required(self):
        for resource in self:
            if resource.product_template_id and not resource.product_id:
                raise ValidationError(_("A Product should be set, as the resource is linked to a product template."))
            if not resource.product_template_id and resource.product_id:
                raise ValidationError(_("A Product should be set, as the resource is linked to a product template."))
            if resource.product_template_id and resource.product_id:
                if resource.product_id not in resource.product_template_id.with_context(active_test=False).product_variant_ids:
                    raise ValidationError(_("The resource product should be related to the product template."))

    @api.model_create_multi
    def create(self, list_values):
        # optimized with batch prefetching
        product_template_ids = [val['product_template_id'] for val in list_values if val.get('product_template_id')]
        product_template_map = {tmpl.id: tmpl.product_variant_id.id for tmpl in self.env['product.template'].browse(product_template_ids)}
        product_product_ids = [val['product_id'] for val in list_values if val.get('product_id')]
        product_product_map = {product.id: product.product_tmpl_id.id for product in self.env['product.product'].browse(product_product_ids)}

        for values in list_values:
            if values.get('product_template_id') and not values.get('product_id'):  # deduce product variant from template
                values['product_id'] = product_template_map.get(values['product_template_id'])

            if not values.get('product_template_id') and values.get('product_id'):  # deduce product template from variant
                values['product_template_id'] = product_product_map.get(values['product_id'])

            if values.get('product_template_id'):  # force material
                values['resource_type'] = 'material'

        return super(Resource, self).create(list_values)

    def write(self, values):
        if values.get('product_id') and 'product_template_id' not in values:
            values['product_template_id'] = self.env['product.product'].with_context(active_test=False).browse(values['product_id']).product_template_id.id

        if values.get('product_template_id') and 'product_id' not in values:
            values['product_id'] = self.env['product.template'].with_context(active_test=False).browse(values['product_template_id']).product_variant_id.id

        if 'product_template_id' in values and not values.get('product_template_id'):
            values['product_id'] = False

        return super(Resource, self).write(values)

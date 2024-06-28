# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Resource(models.Model):
    _inherit = 'resource.resource'

    product_template_id = fields.Many2one(related='product_id.product_tmpl_id', store=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('can_be_rented', '=', True), ('rental_tracking', '=', 'use_resource')])

    @api.onchange('product_template_id')
    def _onchange_product_template_id(self):
        if not self.product_template_id:
            self.product_id = False
        else:
            self.product_id = self.product_template_id.product_variant_id

    @api.constrains('product_template_id', 'product_id')
    def _check_product_id_required(self):
        for resource in self:
            if resource.product_id:
                if not resource.product_id.can_be_rented or not resource.product_id.rental_tracking == 'use_resource':
                    raise ValidationError(_("The resource product should be rentable and track its resources."))

    @api.model_create_multi
    def create(self, list_values):
        for values in list_values:
            if values.get('product_id'):  # force material
                values['resource_type'] = 'material'

        return super(Resource, self).create(list_values)

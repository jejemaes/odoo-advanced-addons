
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    require_customer = fields.Selection([
        ('no', 'Optional'),
        ('payment', 'Required after payment'),
        ('order', 'Required before payment'),
    ], string='Require Customer', default='no', help="Prevent to go further if the customer is not set on the order.")

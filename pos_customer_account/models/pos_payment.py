from odoo import api, fields, models
from odoo.osv import expression


class PosPayment(models.Model):
    _inherit = "pos.payment"

    partner_id = fields.Many2one(store=True)
    payment_method_type = fields.Selection(related='payment_method_id.type')



class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    journal_type = fields.Selection(related='journal_id.type', store=True)
    type = fields.Selection(search='_search_type')

    @api.model
    def _search_type(self, operator, value):
        if value == 'pay_later':
            new_values = ['cash', 'bank']
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = [('journal_id.type', 'in', new_values)]
            else:
                domain = ['|', ('journal_id.type', 'not in', new_values), ('journal_id', '=', None)]
        else:
            domain = [('journal_id.type', operator, value)]
        return domain

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class PosPaymentChange(models.TransientModel):
    _name = 'pos.payment.change'
    _description = "PoS Payment Change Method"

    @api.model
    def default_get(self, fields):
        result = super(PosPaymentChange, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model and active_model != 'pos.payment':
            raise UserError('This action can only be done on PoS Payment.')

        active_ids = self._context.get('active_ids')
        if 'pos_payment_ids' in fields and active_ids:
            result['pos_payment_ids'] = [(6, 0, active_ids)]
        return result

    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', domain=[('type', '!=', 'pay_later')], required=True)

    pos_payment_ids = fields.Many2many('pos.payment', string='Payments')
    pos_payment_count = fields.Integer("Payment Count", compute='_compute_pos_payment_ids')
    pos_payment_amount = fields.Monetary("Total Amount", compute='_compute_pos_payment_amount')
    currency_id = fields.Many2one('res.currency', "Currency", required=True, default=lambda self: self.env.company.currency_id)

    @api.depends('pos_payment_ids')
    def _compute_pos_payment_ids(self):
        for wizard in self:
            wizard.pos_payment_count = len(wizard.pos_payment_ids)

    @api.depends('pos_payment_ids', 'currency_id')
    def _compute_pos_payment_amount(self):
        # TODO : no multi currency handled here ...
        for wizard in self:
            wizard.pos_payment_amount = sum(wizard.pos_payment_ids.mapped('amount'))

    def action_change_payment_method(self):
        if self.mapped('pos_payment_ids').filtered(lambda p: p.payment_method_type != 'pay_later'):
            raise UserError('Some payment are already marked as paid. Please select only payment with "pay later" method.')

        self.mapped('pos_payment_ids').write({
            'payment_method_id': self.payment_method_id.id,
            'card_type': "Deferred Payment"
        })
        return True

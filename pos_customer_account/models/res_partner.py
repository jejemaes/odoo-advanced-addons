
from odoo import api, fields, models, _
from odoo.osv import expression


class Partner(models.Model):
    _inherit = "res.partner"

    def action_pay_late_pos_payment(self):
        later_method = self.env['pos.payment.method'].search([('type', '=', 'pay_later')])

        payment_ids = self.env['pos.payment'].search([('payment_method_id', 'in', later_method.ids), ('partner_id', '=', self.id)]).ids
        default_payment_method = self.env['pos.payment.method'].search([('type', '!=', 'pay_later')], limit=1)

        context = dict(self.env.context)

        wizard = self.env['pos.payment.change'].create({
            'pos_payment_ids': [(6, 0, payment_ids)],
            'payment_method_id': default_payment_method.id,
        })
        return {
            'name': _('Pay all late payment for %s') % (self.display_name,),
            'view_mode': 'form',
            'res_model': 'pos.payment.change',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': wizard.id,
            'context': context,
        }

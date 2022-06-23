# -*- coding: utf-8 -*-

from odoo import models


class Document(models.Model):
    _inherit = 'document.document'

    def _generate_record_values(self, model_name, subtype=False):
        if model_name == 'account.move':
            journal = self.env['account.move'].with_context(default_move_type=subtype)._get_default_journal()
            base_values = {
                'move_type': subtype,
                'journal_id': journal.id,
            }
            if subtype not in ['out_refund', 'out_invoice']:
                base_values['narration'] = False

            value_list = []
            for document in self:
                values = dict(base_values)

                if document.partner_id:
                    values['partner_id'] = document.partner_id.id

                value_list.append(values)
            return value_list

        return super(Document, self)._generate_record_values(model_name, subtype=subtype)

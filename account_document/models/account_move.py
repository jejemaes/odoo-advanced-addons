# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'document.mixin']

    def _document_get_tags(self):
        if self.move_type == 'in_invoice':
            return self.company_id.document_account_in_invoice_tag_ids
        if self.move_type == 'out_invoice':
            return self.company_id.document_account_out_invoice_tag_ids
        if self.move_type == 'in_refund':
            return self.company_id.document_account_in_refund_tag_ids
        if self.move_type == 'out_refund':
            return self.company_id.document_account_out_refund_tag_ids
        return self.company_id.document_default_tag_ids

    def _document_get_folder(self):
        if self.move_type == 'in_invoice':
            return self.company_id.document_account_in_invoice_folder_id
        if self.move_type == 'out_invoice':
            return self.company_id.document_account_out_invoice_folder_id
        if self.move_type == 'in_refund':
            return self.company_id.document_account_in_refund_folder_id
        if self.move_type == 'out_refund':
            return self.company_id.document_account_out_refund_folder_id
        return None

    def _document_can_create(self):
        return super(AccountMove, self)._document_can_create() and self.company_id.document_account_active

    def _document_record_type_selection(self):
        return [
            ('account.move/in_invoice', "Vendor Bill"),
            ('account.move/out_invoice', "Customer Invoice"),
            ('account.move/in_refund', "Vendor Credit Note"),
            ('account.move/out_refund', "Credit Note")
        ]

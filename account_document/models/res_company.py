# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    document_account_active = fields.Boolean("Document in Accounting")

    document_account_in_invoice_folder_id = fields.Many2one('document.folder', string="Vendor Bill Folder")
    document_account_in_invoice_tag_ids = fields.Many2many('document.tag', 'document_tag_res_company_account_in_invoice_rel', string="Vendor Bill Tags")

    document_account_out_invoice_folder_id = fields.Many2one('document.folder', string="Customer Invoice Folder")
    document_account_out_invoice_tag_ids = fields.Many2many('document.tag', 'document_tag_res_company_account_out_invoice_rel', string="Customer Invoice Tags")

    document_account_in_refund_folder_id = fields.Many2one('document.folder', string="Vendor Credit Note Folder")
    document_account_in_refund_tag_ids = fields.Many2many('document.tag', 'document_tag_res_company_account_in_refund_rel', string="Vendor Credit Note Tags")

    document_account_out_refund_folder_id = fields.Many2one('document.folder', string="Credit Note Folder")
    document_account_out_refund_tag_ids = fields.Many2many('document.tag', 'document_tag_res_company_account_out_refund_rel', string="Credit Note Tags")

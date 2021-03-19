# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    document_account_active = fields.Boolean(related='company_id.document_account_active', readonly=False)

    document_account_in_invoice_folder_id = fields.Many2one(related='company_id.document_account_in_invoice_folder_id', readonly=False)
    document_account_in_invoice_tag_ids = fields.Many2many(related='company_id.document_account_in_invoice_tag_ids', readonly=False)

    document_account_out_invoice_folder_id = fields.Many2one(related='company_id.document_account_out_invoice_folder_id', readonly=False)
    document_account_out_invoice_tag_ids = fields.Many2many(related='company_id.document_account_out_invoice_tag_ids', readonly=False)

    document_account_in_refund_folder_id = fields.Many2one(related='company_id.document_account_in_refund_folder_id', readonly=False)
    document_account_in_refund_tag_ids = fields.Many2many(related='company_id.document_account_in_refund_tag_ids', readonly=False)

    document_account_out_refund_folder_id = fields.Many2one(related='company_id.document_account_out_refund_folder_id', readonly=False)
    document_account_out_refund_tag_ids = fields.Many2many(related='company_id.document_account_out_refund_tag_ids', readonly=False)

    # ui
    document_account_in_invoice_selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_document_account_in_invoice_selectable_tag_ids', store=False)
    document_account_out_invoice_selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_document_account_out_invoice_selectable_tag_ids', store=False)
    document_account_in_refund_selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_document_account_in_refund_selectable_tag_ids', store=False)
    document_account_out_refund_selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_document_account_out_refund_selectable_tag_ids', store=False)

    @api.depends('document_account_in_invoice_folder_id')
    def _compute_document_account_in_invoice_selectable_tag_ids(self):
        self._compute_selectable_tag_ids('in_invoice')

    @api.depends('document_account_out_invoice_folder_id')
    def _compute_document_account_out_invoice_selectable_tag_ids(self):
        self._compute_selectable_tag_ids('out_invoice')

    @api.depends('document_account_in_refund_folder_id')
    def _compute_document_account_in_refund_selectable_tag_ids(self):
        self._compute_selectable_tag_ids('in_refund')

    @api.depends('document_account_out_refund_folder_id')
    def _compute_document_account_out_refund_selectable_tag_ids(self):
        self._compute_selectable_tag_ids('out_refund')

    def _compute_selectable_tag_ids(self, move_type, ):
        for company in self:
            if company['document_account_' + move_type + '_folder_id']:
                company['document_account_' + move_type + '_selectable_tag_ids'] = self.env['document.tag'].search(['|', ('folder_id', '=', False), ('folder_id', 'parent_of', company['document_account_' + move_type + '_folder_id'].id)])
            else:
                company['document_account_' + move_type + '_selectable_tag_ids'] = None

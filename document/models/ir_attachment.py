# -*- coding: utf-8 -*-

from odoo import api, fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    document_ids = fields.One2many('document.document', 'attachment_id')
    document_count = fields.Integer('Document Count', compute='_compute_document_count')
    document_can_generate = fields.Boolean(compute='_compute_document_can_generate')

    @api.depends('document_ids')
    def _compute_document_count(self):
        data = self.env['document.document'].read_group([('attachment_id', 'in', self.ids)], fields=['attachment_id'], groupby=['attachment_id'])
        document_count_dict = dict((d['attachment_id'][0], d['attachment_id_count']) for d in data)
        for attachment in self:
            attachment.document_count = document_count_dict.get(attachment.id, 0)

    @api.depends('res_model', 'res_id', 'res_field')
    def _compute_document_can_generate(self):
        for attachment in self:
            can_generate = False
            if not attachment.document_count:  # limit to one document per attachment one2one relation, without unique constraint
                if attachment.res_model and attachment.res_id and not attachment.res_field:  # attachment must be attached to record
                    if issubclass(type(self.env[attachment.res_model]), self.pool['document.mixin']):  # attached record must implement mixin
                        can_generate = True
            attachment.document_can_generate = can_generate

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super(IrAttachment, self).create(vals_list)
        # context key to avoid auto document generation, just in case...
        if not self._context.get('document_no_create'):
            attachments._document_generate()
        return attachments

    def write(self, values):
        resutl = super(IrAttachment, self).write(values)
        if not self._context.get('document_no_create'):
            if 'res_model' in values or 'res_id' in values:
                self._document_generate()

    def _document_generate(self):
        res_model_attachment_map = {}
        for attachment in self:
            if attachment.document_can_generate:
                res_model_attachment_map.setdefault(attachment.res_model, []).append(attachment)

        document_value_list = []
        for res_model, attachment_list in res_model_attachment_map.items():
            res_ids = [attachment.res_id for attachment in attachment_list]
            for record, attachment in zip(self.env[res_model].browse(res_ids), attachment_list):
                values = record._document_get_create_values(attachment)
                if values:
                    document_value_list.append(values)

        return self.env['document.document'].create(document_value_list)

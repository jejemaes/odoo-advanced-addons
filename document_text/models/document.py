# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Document(models.Model):
    _inherit = 'document.document'

    handler = fields.Selection(selection_add=[('text', 'Text')], ondelete={'text': 'cascade'})
    raw_text = fields.Html(compute='_compute_raw_text', inverse='_inverse_raw_text')

    @api.depends('raw', 'handler')
    def _compute_raw_text(self):
        for document in self:
            if document.handler == 'text':
                document.raw_text = document.with_context(bin_size=False).raw
            else:
                document.raw_text = None

    def _inverse_raw_text(self):
        for document in self:
            if document.handler == 'text':
                document.raw = document.with_context(bin_size=False).raw_text

    @api.onchange('handler')
    def _onchange_handler_text(self):
        if self.handler != 'text':
            self.mimetype = False

    @api.model
    def create(self, values):
        handler = values.get('handler', self.default_get(['handler'])['handler'])
        if handler == 'text':
            values['mimetype'] = 'text/html'
        return super(Document, self).create(values)

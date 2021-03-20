# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DocumentAttachRecord(models.TransientModel):
    _name = 'document.attach.record'
    _description = "Attah Documents to existing Record"

    @api.model
    def default_get(self, fields):
        result = super(DocumentAttachRecord, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'document.document':
            raise UserError(_("You can only apply this action from a document."))

        if self._context.get('active_id'):
            result['document_ids'] = [(6, 0, [self._context.get('active_ids')])]
        if self._context.get('active_ids'):
            result['document_ids'] = [(6, 0, self._context.get('active_ids'))]
        return result

    document_ids = fields.Many2many('document.document', string="Documents", required=True)
    resource_ref = fields.Reference(string='Record', selection='_selection_target_model', required=True)

    @api.model
    def _selection_target_model(self):
        domain = [('is_mail_thread', '=', True), ('transient', '=', False), ('model', '!=', 'document.document')]
        # in installation mode, we can not check the '_asbstract' in env as registry is not fully loaded
        if self._context.get('install_mode'):
            return [(model.model, model.name) for model in self.env['ir.model'].search(domain)]
        return [(model.model, model.name) for model in self.env['ir.model'].search(domain) if not self.env[model.model]._abstract]

    def action_attach_record(self):
        # check no document is already attached to record
        for document in self.document_ids:
            if document.res_model or document.res_id:
                raise UserError(_("The document %s is already attached to a record.") % (document.name,))

        # attach origin document to record
        self.document_ids.write({
            'res_model': self.resource_ref._name,
            'res_id': self.resource_ref.id,
        })

        return True

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DocumentCreateRecord(models.TransientModel):
    _name = 'document.create.record'
    _description = "Create Record from a Document"

    @api.model
    def default_get(self, fields):
        result = super(DocumentCreateRecord, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'document.document':
            raise UserError(_("You can only apply this action from a document."))

        if self._context.get('active_id'):
            result['document_ids'] = [(6, 0, [self._context.get('active_ids')])]
        if self._context.get('active_ids'):
            result['document_ids'] = [(6, 0, self._context.get('active_ids'))]
        return result

    document_ids = fields.Many2many('document.document', string="Documents", required=True)
    record_type = fields.Selection(selection='_selection_record_type', required=True)

    @api.model
    def _selection_record_type(self):
        result = []
        for model_name, model_cls in self.env.items():
            if model_name != 'document.mixin' and issubclass(type(model_cls), self.pool['document.mixin']):
                result += model_cls._document_record_type_selection()
        return result

    def action_create_record(self):
        # check no document is already attached to record
        for document in self.document_ids:
            if document.res_model or document.res_id:
                raise UserError(_("The document %s is already attached to a record.") % (document.name,))

        # extract model name (my.model) and the subtype
        type_parts = self.record_type.split('/')
        model_name = type_parts[0]
        subtype = type_parts[1] if len(type_parts) != 1 else False

        # create records
        documents = self.document_ids.sorted(key='id', reverse=False)
        value_list = documents._generate_record_values(model_name, subtype=subtype)
        records = self.env[model_name].create(value_list)

        # attach origin document to new record
        for document, record in zip(documents, records):
            document.write({
                'res_model': record._name,
                'res_id': record.id,
            })
            document.attachment_id.register_as_main_attachment()

        return records._document_record_get_action()

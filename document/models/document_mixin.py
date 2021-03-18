# -*- coding: utf-8 -*-

from odoo import models


class DocumentMixin(models.AbstractModel):

    _name = 'document.mixin'
    _description = "Document Mixin"

    def _document_get_create_values(self, attachment):
        self.ensure_one()
        if self._document_can_create():
            return {
                'attachment_id': attachment.id,
                'name': attachment.name or self.display_name,
                'folder_id': self._document_get_folder().id,
                'owner_id': self._document_get_owner().id,
                'tag_ids': [(6, 0, self._document_get_tags().ids)],
            }
        return {}

    def _document_get_owner(self):
        return self.env.user

    def _document_get_tags(self):
        return self.env['documents.tag']

    def _document_get_folder(self):
        return self.env['documents.folder']

    def _document_can_create(self):
        return bool(self and self._document_get_folder())

# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class Folder(models.Model):
    _name = 'document.folder'
    _description = 'Document Folder'
    _parent_name = 'parent_id'
    _order = 'sequence, id'
    _check_company_auto = True

    @api.model
    def default_get(self, fields):
        res = super(Folder, self).default_get(fields)
        if self._context.get('folder_id'):
            res['parent_id'] = self._context.get('folder_id')
        return res

    name = fields.Char("Name", required=True, translate=True)
    description = fields.Text("Description")
    document_ids = fields.One2many('document.document', 'folder_id', string="Documents")
    document_count = fields.Integer("Document Count", compute='_compute_document_count')
    sequence = fields.Integer('Sequence', default=10)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, help="This folder will only be available for the selected company")

    parent_id = fields.Many2one('document.folder', string="Parent Folder", ondelete="cascade", check_company=True, help="Tag categories from parent folders will be shared to their sub folders")
    children_ids = fields.One2many('document.folder', 'parent_id', string="Sub-folders")

    facet_ids = fields.One2many('document.facet', 'folder_id', string="Tag Categories", help="Select the tag categories to be used")
    read_group_ids = fields.Many2many('res.groups', 'document_folder_read_group_rel', string="Read Access Groups", help="Groups able to see the workspace and read its documents without create/edit rights.")
    group_ids = fields.Many2many('res.groups', 'document_folder_write_group_rel', string="Write Access Groups", help="Groups able to see the workspace and read/create/edit its documents.")

    @api.depends('document_ids')
    def _compute_document_count(self):
        for folder in self:
            folder.document_count = len(folder.document_ids)  # TODO : use read_group bordel

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive folders.'))

    def name_get(self):
        result = []
        for record in self:
            if record.parent_id:
                result.append((record.id, "%s / %s" % (record.parent_id.sudo().name, record.name)))
            else:
                result.append((record.id, record.name))
        return result

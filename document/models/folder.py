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
    children_count = fields.Integer("Sub-folder Count", compute='_compute_children_count')

    facet_ids = fields.One2many('document.facet', 'folder_id', string="Tag Categories", help="Select the tag categories to be used")
    read_group_ids = fields.Many2many('res.groups', 'document_folder_read_group_rel', string="Read Access Groups", help="Groups able to see the workspace and read its documents without create/edit rights.")
    write_group_ids = fields.Many2many('res.groups', 'document_folder_write_group_rel', string="Write Access Groups", help="Groups able to see the workspace and read/create/edit its documents.")

    @api.depends('document_ids')
    def _compute_document_count(self):
        data = self.env['document.document'].read_group([('folder_id', 'in', self.ids)], fields=['folder_id'], groupby=['folder_id'])
        document_count_dict = dict((d['folder_id'][0], d['folder_id_count']) for d in data)
        for folder in self:
            folder.document_count = document_count_dict.get(folder.id, 0)

    @api.depends('children_ids')
    def _compute_children_count(self):
        data = self.env['document.folder'].read_group([('parent_id', 'in', self.ids)], fields=['parent_id'], groupby=['parent_id'])
        children_count_dict = dict((d['parent_id'][0], d['parent_id_count']) for d in data)
        for folder in self:
            folder.children_count = children_count_dict.get(folder.id, 0)


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

    def action_view_subfolders(self):
        action = self.env.ref('document.document_folder_action_directories').read()[0]
        action['display_name'] = self.name
        action['domain'] = False
        action['context'] = {
            'search_default_parent_id': self.id,
            'default_parent_id': self.id,
        }
        return action

    def action_view_documents(self):
        action = self.env.ref('document.document_document_action').read()[0]
        action['display_name'] = self.name
        action['context'] = {
            'search_default_folder_id': self.id,
            'default_folder_id': self.id,
        }
        return action

# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    document_default_tag_ids = fields.Many2many(related='company_id.document_default_tag_ids', readonly=False)

    default_folder_id = fields.Many2one('document.folder', string="Default Folder", default_model='document.document')

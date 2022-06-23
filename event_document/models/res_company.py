# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    document_event_active = fields.Boolean("Document in Event")
    document_event_specific_folder = fields.Boolean("Event Specific Folder")

    document_event_folder_id = fields.Many2one('document.folder', string="Event Folder")
    document_event_tag_ids = fields.Many2many('document.tag', 'document_tag_res_company_event_rel', string="Default Event Tags")

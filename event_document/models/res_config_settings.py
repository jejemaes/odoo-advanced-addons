# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    document_event_active = fields.Boolean(related='company_id.document_event_active', readonly=False)
    group_document_specific_event = fields.Boolean(string="Event Specific Document Folder", implied_group='event_document.group_document_specific_event')

    document_event_folder_id = fields.Many2one(related='company_id.document_event_folder_id', readonly=False)
    document_event_tag_ids = fields.Many2many(related='company_id.document_event_tag_ids', readonly=False)

    document_event_selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_document_event_selectable_tag_ids', store=False)

    @api.depends('document_event_folder_id')
    def _compute_document_event_selectable_tag_ids(self):
        for config in self:
            if config.document_event_active:
                config.document_event_selectable_tag_ids = self.env['document.tag'].search(['|', ('folder_id', '=', False), ('folder_id', 'parent_of', config.document_event_folder_id.id)])
            else:
                config.document_event_selectable_tag_ids = None

    @api.onchange('document_event_active')
    def _onchange_document_event_active(self):
        if not self.document_event_active:
            self.group_document_specific_event = False
            self.document_event_folder_id = False
            self.document_event_tag_ids = False

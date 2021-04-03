# -*- coding: utf-8 -*-

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    document_folder_creation = fields.Boolean("Folder for Documents", help="When an event linked to this template is in a stage requiring a document folder, the folder will be generated.")
    document_tag_ids = fields.Many2many('document.tag', string="Default Document Tags", domain="[('id', 'in', document_selectable_tag_ids)]", store=True)
    document_selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_document_selectable_tag_ids', store=False)

    @api.depends_context('uid')
    def _compute_document_selectable_tag_ids(self):
        for event in self:
            domain = [('folder_id', '=', False)]
            if self.env.company.document_event_folder_id:
                domain = ['|'] + domain + [('folder_id', 'parent_of', self.env.company.document_event_folder_id.id)]
            event.document_selectable_tag_ids = self.env['document.tag'].search(domain)


class Event(models.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'document.mixin']

    document_folder_id = fields.Many2one('document.folder', string="Document Folder", ondelete='set null')
    document_tag_ids = fields.Many2many('document.tag', string="Addtionnal Document Tags", compute='_compute_document_tag_ids', domain="[('id', 'in', document_selectable_tag_ids)]", store=True, readonly=False)
    document_selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_document_selectable_tag_ids', store=False)

    @api.depends('event_type_id')
    def _compute_document_tag_ids(self):
        for event in self:
            if not event.document_tag_ids and event.event_type_id.document_tag_ids:
                event.document_tag_ids = event.event_type_id.document_tag_ids

    @api.depends('document_folder_id', 'company_id.document_event_folder_id')
    def _compute_document_selectable_tag_ids(self):
        for event in self:
            domain = [('folder_id', '=', False)]
            if event.document_folder_id:
                folder_id = event.document_folder_id.id
            else:
                folder_id = event.company_id.document_event_folder_id.id
            domain = ['|'] + domain + [('folder_id', 'parent_of', folder_id)]
            event.document_selectable_tag_ids = self.env['document.tag'].search(domain)

    # --------------------------------------------------
    # ORM Overrides
    # --------------------------------------------------

    @api.model_create_multi
    def create(self, value_list):
        events = super(Event, self).create(value_list)
        events._generate_document_folder()
        return events

    def write(self, values):
        result = super(Event, self).write(values)
        self._generate_document_folder()
        return result

    # --------------------------------------------------
    # Document Mixin Overrides
    # --------------------------------------------------

    def _document_get_tags(self):
        return self.company_id.document_event_tag_ids | self.document_tag_ids

    def _document_get_folder(self):
        return self.document_folder_id or self.company_id.document_event_folder_id

    def _document_can_create(self):
        return super(Event, self)._document_can_create() and self.company_id.document_event_active

    def _document_record_type_selection(self):
        """ Prevent create event from a document """
        return []

    # --------------------------------------------------
    # Business
    # --------------------------------------------------

    def _generate_document_folder(self):
        for event in self:
            if event.event_type_id.document_folder_creation and event.stage_id.document_folder_required and not event.document_folder_id:
                folder_values = event._prepare_document_folder_values()
                folder = self.env['document.folder'].create(folder_values)
                event.write({'document_folder_id': folder.id})

    def _prepare_document_folder_values(self):
        return {
            'name': self.name,
            'parent_id': self.company_id.document_event_folder_id.id,
            'company_id': self.company_id.id,
        }


class EventStage(models.Model):
    _inherit = 'event.stage'

    document_folder_required = fields.Boolean("Required a Document Folder")

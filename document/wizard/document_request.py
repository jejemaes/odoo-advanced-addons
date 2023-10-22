# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class RequestWizard(models.TransientModel):
    _name = "document.request"
    _description = "Document Request"

    name = fields.Char(required=True)
    owner_id = fields.Many2one('res.users', required=True, string="Owner")
    partner_id = fields.Many2one('res.partner', string="Contact")
    folder_id = fields.Many2one('document.folder', string="Folder", required=True)
    tag_ids = fields.Many2many('document.tag', string="Tags")
    selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_selectable_tag_ids')

    # mail activity
    activity_user_id = fields.Many2one('res.users', required=True, string="Request To", default=lambda self: self.env.user.id)
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string="Activity type",
        domain=[('category', '=', 'upload_file')],
        required=True,
        default=lambda self: self.env.ref('mail.mail_activity_data_upload_document', raise_if_not_found=False),
    )
    activity_date_deadline_range = fields.Integer(string='Due Date In', default=10)
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due type', default='days')
    activity_note = fields.Html(string="Note")

    # attach to record
    resource_ref = fields.Reference(string='Attached To', selection='_selection_target_model', required=False)

    @api.depends('folder_id')
    def _compute_selectable_tag_ids(self):
        for document in self:
            if document.folder_id:
                document.selectable_tag_ids = self.env['document.tag'].search(['|', ('folder_id', '=', False), ('folder_id', 'parent_of', document.folder_id.id)])
            else:
                document.selectable_tag_ids = self.env['document.tag'].search([('folder_id', '=', False)])

    @api.model
    def _selection_target_model(self):
        domain = [('is_mail_thread', '=', True), ('transient', '=', False), ('model', '!=', 'document.document')]
        # in installation mode, we can not check the '_asbstract' in env as registry is not fully loaded
        if self._context.get('install_mode'):
            return [(model.model, model.name) for model in self.env['ir.model'].search(domain)]
        return [(model.model, model.name) for model in self.env['ir.model'].search(domain) if not self.env[model.model]._abstract]

    def _get_document_values(self):
        values = {
            'name': self.name,
            'document_type': 'request',
            'attachment_id': None, # emtpy document !
            'folder_id': self.folder_id.id,
            'tag_ids': [(6, 0, self.tag_ids.ids if self.tag_ids else [])],
            'owner_id': self.env.user.id,
            'partner_id': self.partner_id.id,
        }
        if self.resource_ref:
            values['res_model'] = self.resource_ref._name
            values['res_id'] = self.resource_ref.id
        return values

    def _get_activity_values(self):
        return {
            'user_id': self.activity_user_id.id,
            'note': self.activity_note,
            'activity_type_id': self.activity_type_id.id,
            'summary': self.name
        }

    def action_request(self):
        self.ensure_one()
        document = self.env['document.document'].create(self._get_document_values())

        activity_values = self._get_activity_values()
        activity_values['res_model_id'] = self.env['ir.model']._get(document._name).id
        activity_values['res_id'] = document.id
        self.env['mail.activity'].create(activity_values)

        return True

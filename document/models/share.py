# -*- coding: utf-8 -*-

import uuid
from ast import literal_eval
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class DocumentShare(models.Model):
    _name = 'document.share'
    _description = "Document Share"
    _check_company_auto = True

    @api.model
    def default_get(self, field_list):
        result = super(DocumentShare, self).default_get(field_list)
        if self._context.get('active_model') == 'document.document' and self._context.get('active_ids'):
            if 'document_ids' in field_list and not result.get('document_ids'):
                result['document_ids'] = [(6, 0, self._context.get('active_ids'))]
                result['content_type'] = 'ids'  # force the type
        return result

    name = fields.Char("Name", required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    access_token = fields.Char("Access Token", default=lambda x: str(uuid.uuid4()), groups="document.group_document_user", required=True)
    author_avatar = fields.Image(related='create_uid.partner_id.image_128')

    full_url = fields.Char("URL", compute='_compute_full_url')
    action = fields.Selection([
        ('download', "Download"),
        ('downloadupload', "Download and Upload"),
    ], default='download', string="Allows to", required=True)

    # Default values in case of document creation
    folder_id = fields.Many2one('document.folder', check_company=True)
    tag_ids = fields.Many2many('document.tag', string="Shared Tags")
    owner_id = fields.Many2one('res.users', string="Document Owner")
    partner_id = fields.Many2one('res.partner', string="Contact", check_company=True)

    # ui
    selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_selectable_tag_ids')

    # Validity duration
    date_deadline = fields.Date("Valid Until")
    state = fields.Selection([
        ('live', "Live"),
        ('expired', "Expired"),
    ], compute='_compute_state', string="Status")

    # Type to get concerned documents
    content_type = fields.Selection([
        ('ids', "Document list"),
        ('domain', "Domain"),
    ], default='ids', string="Share Type", required=True)
    document_ids = fields.Many2many('document.document', string="Shared documents", check_company=True)  # Also inlucde uploaded documents
    domain = fields.Char("Domain")

    # Activity
    activity_option = fields.Boolean(string='Create a new activity')
    activity_type_id = fields.Many2one('mail.activity.type', string="Activity Type")
    activity_summary = fields.Char('Summary')
    activity_date_deadline_range = fields.Integer(string='Due Date In')
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due type', default='days')
    activity_note = fields.Html(string="Note")
    activity_user_id = fields.Many2one('res.users', string='Responsible')

    _sql_constraints = [
        ('share_unique', 'UNIQUE(access_token)', "This access token already exists"),
        ('folder_required', "CHECK((action = 'downloadupload' AND folder_id IS NOT NULL) OR (action != 'downloadupload'))", "Folder is required when uploading documents is allowed.")
    ]

    @api.depends('date_deadline')
    def _compute_state(self):
        for record in self:
            state = 'live'
            if record.date_deadline:
                today = fields.Date.from_string(fields.Date.today())
                exp_date = fields.Date.from_string(record.date_deadline)
                diff_time = (exp_date - today).days
                if diff_time <= 0:
                    state = 'expired'
            record.state = state

    @api.depends('access_token')
    def _compute_full_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for share in self:
            if share.id:
                share.full_url = "%s/document/share/%s/%s" % (base_url, share.id, share.access_token)
            else:
                share.full_url = False

    @api.depends('folder_id', 'tag_ids')
    def _compute_selectable_tag_ids(self):
        for share in self:
            if share.folder_id:
                share.selectable_tag_ids = self.env['document.tag'].search(['|', ('folder_id', '=', False), ('folder_id', 'parent_of', share.folder_id.id)])
            else:
                share.selectable_tag_ids = None

    @api.onchange('content_type')
    def _onchange_content_type(self):
        if self.content_type == 'domain':
            if self.action != 'downloadupload':
                self.document_ids = False
        elif self.content_type == 'ids':
            self.domain = False

    @api.onchange('folder_id')
    def _onchange_folder_id(self):
        self.tag_ids = None

    @api.constrains('folder_id', 'tag_ids')
    def _check_tag_in_folder(self):
        for share in self:
            if any(tag not in share.selectable_tag_ids for tag in share.tag_ids):
                raise ValidationError(_("The document's tags must be in the folder ones."))

    # ----------------------------------------------------
    # Business Methods
    # ----------------------------------------------------

    def action_get_share_link(self):
        action = self.env.ref('document.document_share_action_popup_link_only').read()[0]
        action['res_id'] = self.id
        return action

    def get_concerned_documents(self):
        result = {}
        for share in self:
            if share.content_type == 'domain':
                domain = literal_eval(share.domain)
                documents = self.env['document.document'].search(domain)
                if share.action == 'downloadupload':
                    documents += share.document_ids
                result[share.id] = documents
            elif share.content_type == 'ids':
                result[share.id] = share.document_ids
        return result

    def get_document_default_values(self):
        result = {}
        for share in self:
            result[share.id] = {
                'tag_ids': [(6, 0, share.tag_ids.ids)],
                'folder_id': share.folder_id.id,
                'partner_id': share.partner_id.id,
                'owner_id': share.owner_id.id,
            }
        return result

    def _get_download_all_documents_url(self):
        return '/document/download/all/%s/%s' % (self.id, self.sudo().access_token)

    def _get_download_document_url(self, document_id):
        return '/document/download/%s/%s/%s' % (self.id, self.sudo().access_token, document_id)

    def _get_download_document_thumbnail_url(self, document_id):
        return '/document/thumbnail/%s/%s/%s' % (self.id, self.sudo().access_token, document_id)

    def _get_upload_documents_url(self):
        return '/document/upload/%s/%s' % (self.id, self.sudo().access_token)

    def _get_owner_avatar_url(self):
        if self.author_avatar:
            return '/document/owner_avatar/%s/%s' % (self.id, self.sudo().access_token)
        return None

    def _postprocess_upload(self, documents):
        """ Generate an activity based on the 'share' document configuration.
            :param documents: list of the document on which apply the upload configuration
        """
        # add documents to the concerned documents of the sharing link
        self.write({'document_ids': [(4, document.id) for document in documents]})

        # create activity if needed
        if self.activity_option:
            activity_values = {
                'activity_type_id': self.activity_type_id.id,
                'summary': self.activity_summary,
                'note': self.activity_note,
            }
            if self.activity_date_deadline_range > 0:
                activity_values['date_deadline'] = fields.Date.context_today(self) + relativedelta(**{self.activity_date_deadline_range_type: self.activity_date_deadline_range})

            if self.activity_user_id:
                user = self.activity_user_id
            elif self.owner_id:
                user = self.owner_id
            else:
                user = self.env.user
            if user:
                activity_values['user_id'] = user.id

            documents.activity_schedule(**activity_values)

        return documents

# -*- coding: utf-8 -*-

import base64
import os
import mimetypes
import re
import uuid
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools,  _
from odoo.tools import ImageProcess
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class Document(models.Model):
    _name = 'document.document'
    _description = 'Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'ir.attachment': 'attachment_id'}
    _check_company_auto = True
    _order = 'create_date DESC'

    @api.model
    def _default_access_token(self):
        return str(uuid.uuid4())

    attachment_id = fields.Many2one('ir.attachment', "Attachment", ondelete='cascade', required=True)
    name = fields.Char(related='attachment_id.name', inherited=True, readonly=True)  # as it now contents the filename (with the extension required to server file properly), better to make it readonly
    url = fields.Char(related='attachment_id.url', inherited=True, readonly=False)
    description = fields.Text(related='attachment_id.description', inherited=True, readonly=False)
    type = fields.Text(related='attachment_id.type', inherited=True, readonly=False)
    company_id = fields.Many2one(related='attachment_id.company_id', inherited=True, readonly=True, required=True)
    filename = fields.Char("Filename", compute='_compute_filename', help="Name of the file of this one is donwloaded")
    access_token = fields.Char(related='attachment_id.access_token', inherited=True, default=_default_access_token)  # all documents will have an access token on their attachment

    thumbnail = fields.Binary("Thumbnail", compute='_compute_thumbnail')
    thumbnail_url = fields.Char("Thumbnail Url", compute='_compute_thumbnail_url')
    is_previewable = fields.Boolean("Is Previewable", compute='_compute_is_previewable')
    partner_id = fields.Many2one('res.partner', string="Contact", ondelete="restrict", tracking=True, index=True, check_company=True)
    folder_id = fields.Many2one('document.folder', string="Folder", required=True, ondelete="restrict", tracking=True, index=True, check_company=True)
    favorite_user_ids = fields.Many2many('res.users', 'document_document_user_favorite_rel', 'document_id', 'user_id', string="Favorites")
    tag_ids = fields.Many2many('document.tag', 'document_tag_rel', string="Tags")

    raw_type = fields.Selection([], string="Raw Type", help="Technical field to determine what is store in the 'raw' field.", default=None)
    res_model_name = fields.Char("Related Model Name", compute='_compute_res_model_name')

    is_locked = fields.Boolean("Is Locked", compute='_compute_is_locked')
    lock_uid = fields.Many2one('res.users', string="Locked by")
    owner_id = fields.Many2one('res.users', default=lambda self: self.env.user.id, string="Owner", tracking=True)
    active = fields.Boolean("Active", default=True)

    _sql_constraints = [
        ('attachment_unique', 'UNIQUE(attachment_id)', "Attachment can only be linked to one document."),
    ]

    @api.depends('attachment_id.name', 'attachment_id.mimetype')
    def _compute_filename(self):
        for document in self:
            extension = os.path.splitext(document.name or '')[1]
            extension = extension if extension else mimetypes.guess_extension(document.mimetype or '')
            filename = document.name
            document.filename = filename if os.path.splitext(filename)[1] else filename + extension

    @api.depends('attachment_id.res_model', 'attachment_id.res_id', 'attachment_id.res_field')
    def _compute_res_model_name(self):
        ir_model_names = self.sudo().mapped('res_model')
        ir_models = self.env['ir.model'].sudo().search([('model', 'in', self.mapped('res_model'))]) if ir_model_names else []
        ir_model_map = {model.model: model for model in ir_models}

        for document in self:
            if document.res_id and document.res_model and not document.res_field and document.res_model in ir_model_map:
                document.res_model_name = ir_model_map[document.res_model].name
            else:
                document.res_model_name = False

    @api.depends('lock_uid')
    def _compute_is_locked(self):
        for document in self:
            document.is_locked = bool(document.lock_uid)

    @api.depends('mimetype')
    def _compute_thumbnail(self):
        for document in self:
            if document.mimetype in self._get_thumbnail_mimetypes():
                image = ImageProcess(document.datas)
                width, height = image.image.size
                square_size = width if width > height else height
                image.crop_resize(square_size, square_size)
                image.image = image.image.resize((128, 128))
                document.thumbnail = image.image_base64(output_format='PNG')
            else:
                document.thumbnail = False

    @api.depends('mimetype', 'checksum')
    def _compute_thumbnail_url(self):
        for document in self:
            thumbnail_url = False
            if document.mimetype in self._get_thumbnail_mimetypes() and document.checksum:
                thumbnail_url = '/web/image/%s?model=%s&field=thumbnail&unique=%s' % (document.id, document._name, document.checksum[-8])
            else:
                if document.url:  # find the youtube video thumbnail
                    pattern = r'(?:https?:\/\/)?(?:[0-9A-Z-]+\.)?(?:youtube|youtu|youtube-nocookie)\.(?:com|be)\/(?:watch\?v=|watch\?.+&v=|embed\/|v\/|.+\?v=)?([^&=\n%\?]{11})'
                    youtube_video_tokens = re.findall(pattern, document.url, re.MULTILINE | re.IGNORECASE)
                    if youtube_video_tokens:
                        thumbnail_url = "https://img.youtube.com/vi/%s/0.jpg" % (youtube_video_tokens[0],)
            document.thumbnail_url = thumbnail_url

    @api.depends('mimetype', 'url', 'type')
    def _compute_is_previewable(self):
        for document in self:
            if document.type == 'binary':
                if document.mimetype:
                    if document.mimetype.find('pdf') > -1 or re.match('image.*(gif|jpe|jpg|png)', document.mimetype):
                        document.is_previewable = True
                    else:
                        document.is_previewable = False
                else:
                    document.is_previewable = False
            elif document.type == 'url':
                if document.url:
                    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
                    youtube_regex_match = re.match(youtube_regex, document.url)
                    if youtube_regex_match:
                        document.is_previewable = True
                    else:
                        document.is_previewable = False
                else:
                    document.is_previewable = False
            else:
                document.is_previewable = False


    @api.onchange('url')
    def _onchange_url(self):
        if self.url:
            self.name = self.url[self.url.rfind('/')+1:]

    @api.onchange('folder_id')
    def _onchange_folder_id(self):
        self.tag_ids = None

        if self.folder_id:
            return {'domain': {'tag_ids': [('folder_id', 'parent_of', self.folder_id.id)]}}
        return {'domain': {'tag_ids': []}}

    def unlink(self):
        #  TODO Remove the related attachment
        if not self.user_has_groups('document.group_document_manager'):
            if any(document.lock_uid and document.lock_uid != self.env.user for document in self):
                raise UserError(_("Locked Document can not be removed"))
        return super(Document, self).unlink()

    # -------------------------------------------------------------
    # Mail Gateway
    # -------------------------------------------------------------
    @api.model
    def message_new(self, msg, custom_values=None):
        # copy original custom values for reel document
        original_custom_values = dict(custom_values)

        # create the empty document as achived
        custom_values['active'] = False
        empty_document = super(Document, self).message_new(msg, custom_values=custom_values)

        # process the attachment to create documents
        email_to = msg.get('to')
        if email_to:
            # extract before @ parts
            email_to_localparts = [
                e.split('@', 1)[0].lower()
                for e in (tools.email_split(email_to) or [''])
            ]
            # find the sharing object, via its alias name
            share = self.env['documents.share'].search([
                ('alias_name', 'in', email_to_localparts),
                ('alias_model_id.model', '=', self._name)
            ], limit=1)

            # generate a document record per attachment of the original email
            if share.email_drop:
                document_value_list = []
                if msg.get('attachments'):  # list of nametupled, defined in `self._Attachment` of mail.thread
                    for attachment_namedtuple in msg.get('attachments', []):
                        name, content, dummy = attachment_namedtuple
                        document_values = {
                            'name': name,
                            'datas': base64.b64encode(content),
                            'type': 'binary',
                            'description': name,
                        }
                        document_values.update(original_custom_values)
                        document_value_list.append(document_values)

                # create document from attachments
                documents = self.env['docuemnt.document'].create(document_value_list)
                # log a note to  simulate the create record message
                for document in documents:
                    document._message_log(body=_("This document was created from the attachment from an email."))
                # post process the upload through the sharing (activities, ...)
                share._postprocess_upload(documents)

        return empty_document

    # -------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------

    def action_toggle_favorite(self):
        for document in self:
            document.write({'favorite_user_ids': [(3 if self.env.user in document.favorite_user_ids else 4, self.env.user.id)]})

    def action_toggle_lock(self):
        self.ensure_one()
        if self.lock_uid:
            if self.env.user == self.lock_uid or self.env.user._is_admin() or self.user_has_groups('document.group_document_manager'):
                self.lock_uid = False
        else:
            self.lock_uid = self.env.uid

    def action_share(self):
        action = self.env.ref('document.document_share_action_select_document').read()[0]
        # convert context string to dict
        context = {}
        if action.get('context'):
            eval_context = self.env['ir.actions.actions']._get_eval_context()
            context = safe_eval(action['context'], eval_context)
        # update the context to force `active_ids, and sharing link default name
        context['active_ids'] = self.ids
        if not context.get('default_name'):
            context['default_name'] = _("Sharing of %s") % (self.name,)
        # set new context to the action
        action['context'] = context
        return action

    def action_download(self):
        if len(self) == 1:
            target_url = self.url
            if self.type == 'binary':
                target_url = "/web/content/%s?model=%s&field=datas&download=1" % (self.id, self._name)
        else:
            ids_as_string = [str(_id) for _id in self.ids]
            target_url = '/document/zip_download/%s' % (','.join(ids_as_string),)
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': target_url,
        }

    def action_related_record(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.res_id,
            'res_model': self.res_model,
            'name': self.res_model_name,
        }

    # -------------------------------------------------------------
    # Business
    # -------------------------------------------------------------

    @api.model
    def _get_thumbnail_mimetypes(self):
        return ['image/gif', 'image/jpe', 'image/jpeg', 'image/jpg', 'image/gif', 'image/png']

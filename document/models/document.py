# -*- coding: utf-8 -*-

import base64
from collections import defaultdict
import itertools
import os
import mimetypes
import re
import uuid


from odoo import api, fields, models, tools,  _
from odoo.tools import ImageProcess
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


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

    @api.model
    def _default_tag_ids(self):
        return self.env.company.document_default_tag_ids.ids

    attachment_id = fields.Many2one('ir.attachment', "Attachment", ondelete='cascade', required=True, auto_join=True)
    name = fields.Char(related='attachment_id.name', inherited=True, readonly=True)  # as it now contents the filename (with the extension required to server file properly), better to make it readonly
    url = fields.Char(related='attachment_id.url', inherited=True, readonly=False)
    description = fields.Text(related='attachment_id.description', inherited=True, readonly=False)
    type = fields.Selection(related='attachment_id.type', inherited=True, readonly=False)
    company_id = fields.Many2one(related='attachment_id.company_id', inherited=True, readonly=True, required=True)
    filename = fields.Char("Filename", compute='_compute_filename', help="Name of the file of this one is donwloaded")
    access_token = fields.Char(related='attachment_id.access_token', inherited=True, default=_default_access_token)  # all documents will have an access token on their attachment

    thumbnail = fields.Binary("Thumbnail", compute='_compute_thumbnail')
    thumbnail_url = fields.Char("Thumbnail Url", compute='_compute_thumbnail_url')
    is_previewable = fields.Boolean("Is Previewable", compute='_compute_is_previewable')
    partner_id = fields.Many2one('res.partner', string="Contact", ondelete="restrict", tracking=True, index=True, check_company=True)
    folder_id = fields.Many2one('document.folder', string="Folder", required=True, ondelete="restrict", tracking=True, index=True, check_company=True)
    favorite_user_ids = fields.Many2many('res.users', 'document_document_user_favorite_rel', 'document_id', 'user_id', string="Favorites")
    tag_ids = fields.Many2many('document.tag', 'document_tag_rel', string="Tags", default=_default_tag_ids)

    handler = fields.Selection([('attachment', 'Attachment')], string="Raw Type", default='attachment', required=True, help="Technical field to determine what is store in the 'raw' field.")
    res_model_name = fields.Char("Related Model Name", compute='_compute_res_model_name')

    is_locked = fields.Boolean("Is Locked", compute='_compute_is_locked')
    lock_uid = fields.Many2one('res.users', string="Locked by")
    owner_id = fields.Many2one('res.users', default=lambda self: self.env.user.id, string="Owner", tracking=True)
    active = fields.Boolean("Active", default=True)

    # ui
    selectable_tag_ids = fields.Many2many('document.tag', compute='_compute_selectable_tag_ids')

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

    @api.depends('folder_id', 'tag_ids')
    def _compute_selectable_tag_ids(self):
        for document in self:
            if document.folder_id:
                document.selectable_tag_ids = self.env['document.tag'].search(['|', ('folder_id', '=', False), ('folder_id', 'parent_of', document.folder_id.id)])
            else:
                document.selectable_tag_ids = None

    @api.onchange('url')
    def _onchange_url(self):
        if self.url:
            self.name = self.url[self.url.rfind('/')+1:]

    @api.onchange('folder_id')
    def _onchange_folder_id(self):
        if not self.tag_ids:
            self.tag_ids = self._default_tag_ids()
        else:
            self.tag_ids = self.tag_ids & self.selectable_tag_ids

    def unlink(self):
        #  TODO Remove the related attachment
        if not self.user_has_groups('document.group_document_manager'):
            if any(document.lock_uid and document.lock_uid != self.env.user for document in self):
                raise UserError(_("Locked Document can not be removed"))
        return super(Document, self).unlink()

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        ids = super(Document, self)._search(args, offset=offset, limit=limit, order=order,
                                                count=False, access_rights_uid=access_rights_uid)

        if self.env.is_superuser():
            # rules do not apply for the superuser
            return len(ids) if count else ids

        if not ids:
            return 0 if count else []

        # Work with a set, as list.remove() is prohibitive for large lists of documents
        # (takes 20+ seconds on a db with 100k docs during search_count()!)
        orig_ids = ids
        ids = set(ids)

        # For attachments, the permissions of the document they are attached to
        # apply, so we must remove attachments for which the user cannot access
        # the linked document.
        # Use pure SQL rather than read() as it is about 50% faster for large dbs (100k+ docs),
        # and the permissions are checked in super() and below anyway.
        model_documents = defaultdict(lambda: defaultdict(set))   # {res_model: {res_id: set(ids)}}
        binary_fields_attachments = set()
        self._cr.execute("""
            SELECT D.id, A.res_model, A.res_id, A.public, A.res_field
            FROM ir_attachment A
                LEFT JOIN document_document D ON (D.attachment_id = A.id)
            WHERE D.id IN %s""", [tuple(ids)])
        for row in self._cr.dictfetchall():
            if not row['res_model'] or row['public']:
                continue
            # model_documents = {res_model: {res_id: set(ids)}}
            model_documents[row['res_model']][row['res_id']].add(row['id'])
            # Should not retrieve binary fields attachments
            if row['res_field']:
                binary_fields_attachments.add(row['id'])

        if binary_fields_attachments:
            ids.difference_update(binary_fields_attachments)

        # To avoid multiple queries for each attachment found, checks are
        # performed in batch as much as possible.
        for res_model, targets in model_documents.items():
            if res_model not in self.env:
                continue
            if not self.env[res_model].check_access_rights('read', False):
                # remove all corresponding attachment ids
                ids.difference_update(itertools.chain(*targets.values()))
                continue
            # filter ids according to what access rules permit
            target_ids = list(targets)
            allowed = self.env[res_model].with_context(active_test=False).search([('id', 'in', target_ids)])
            for res_id in set(target_ids).difference(allowed.ids):
                ids.difference_update(targets[res_id])

        # sort result according to the original sort ordering
        result = [id for id in orig_ids if id in ids]

        # If the original search reached the limit, it is important the
        # filtered record set does so too. When a JS view receive a
        # record set whose length is below the limit, it thinks it
        # reached the last page. To avoid an infinite recursion due to the
        # permission checks the sub-call need to be aware of the number of
        # expected records to retrieve
        if len(orig_ids) == limit and len(result) < self._context.get('need', limit):
            need = self._context.get('need', limit) - len(result)
            result.extend(self.with_context(need=need)._search(args, offset=offset + len(orig_ids),
                                       limit=limit, order=order, count=count,
                                       access_rights_uid=access_rights_uid)[:limit - len(result)])

        return len(result) if count else list(result)


    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        result = super(Document, self).search_panel_select_range(field_name)

        if self._context.get('search_panel_expand_folder'):  # this does not work as search_panel don't propagate action context

            if field_name == 'folder_id':
                enable_counters = kwargs.get('enable_counters', False)
                already_fetch_ids = [item['id'] for item in result.get('values', [])]
                additionnal_folders = self.env['document.folder'].with_context(hierarchical_naming=False).search([('id', 'not in', already_fetch_ids)])
                additionnal_result = []
                for folder in additionnal_folders:
                    values = {
                        'id': folder.id,
                        'display_name': folder.display_name,
                        'parent_id': folder.parent_id.id
                    }
                    if enable_counters:
                        values['__count'] = 0
                    additionnal_result.append(values)
                result['values'] += additionnal_result

        return result

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

    def _generate_record_values(self, model_name, subtype=False):
        return []

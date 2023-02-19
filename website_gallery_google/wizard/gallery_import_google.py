# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GalleryImportGoogle(models.TransientModel):
    _name = 'website.gallery.import.google'
    _inherit = ['google.token.status.mixin']
    _description = "Create Gallery from Google"

    @api.model
    def default_get(self, fields):
        active_model = self._context.get('active_model')
        if active_model != 'website.gallery':
            raise UserError(_('You can only apply this action from gallery.'))
        return super(GalleryImportGoogle, self).default_get(fields)

    @api.model
    def _default_website(self):
        website = self.env['website'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)
        if not website:
            website = self.env['website'].search([], limit=1)
        return website

    next_page_token = fields.Char("Next Page Google Token", readonly=True)
    line_ids = fields.One2many('website.gallery.import.google.line', 'wizard_id', "Lines")
    website_id = fields.Many2one('website', 'Website', required=True, default=_default_website)
    user_id = fields.Many2one(string="Public User")

    @api.onchange('website_id')
    def _onchange_website_id(self):
        if self.website_id:
            self.user_id = self.website_id.user_id

    # ----------------------------------------------------------------------------
    # Actions
    # ----------------------------------------------------------------------------

    def action_load_google_galleries(self):
        google_albums, next_page_token = self.env['google.api'].sudo(self.user_id)._photos_fetch_albums()

        # update token
        self.next_page_token = next_page_token
        if not self.next_page_token:
            self.line_ids.unlink()

        # create new album lines
        lines = self.env['website.gallery.import.google.line']
        for data in google_albums:
            line_values = self._prepare_line_values(data)
            lines |= self.env['website.gallery.import.google.line'].create(line_values)

        # refresh wizard by returning the action with wizard id
        action = self.env.ref('website_gallery_google.website_gallery_import_google_action').read()[0]
        action['res_id'] = self.id
        return action

    def action_import(self):
        galleries = self.env['website.gallery']
        for line in self.line_ids:
            if not line.already_import and line.to_import:
                gallery_values = line._prepare_gallery_values()
                galleries |= self.env['website.gallery'].create(gallery_values)
        galleries._google_import_photos()
        return False

    # ----------------------------------------------------------------------------
    # Business Methods
    # ----------------------------------------------------------------------------

    def _prepare_line_values(self, data):
        return {
            'wizard_id': self.id,
            'album_name': data['title'],
            'album_identifier': data['id'],
            'picture_count': data['mediaItemsCount'],
        }

    def _get_return_url_for_auth(self):
        action = self.env.ref('website_gallery.action_website_gallery')
        return '/web?action=%s' % (action.id,)


class GalleryImportGoogleLine(models.TransientModel):
    _name = 'website.gallery.import.google.line'
    _description = "Create Gallery from Google line"
    _order = 'id,create_date'

    wizard_id = fields.Many2one('website.gallery.import.google', required=True)
    album_name = fields.Char("Album Name", readonly=True)
    album_identifier = fields.Char("Album Identifier", readonly=True)
    already_import = fields.Boolean("Already Imported", compute='_compute_already_import')
    to_import = fields.Boolean("To Import")
    picture_count = fields.Integer("Number of pictures", readonly=True)

    @api.depends('album_identifier')
    def _compute_already_import(self):
        google_identifier_values = self.env['website.gallery'].sudo().search_read([('google_identifier', 'in', self.mapped('album_identifier'))], ['google_identifier'])
        google_identifier = [item['google_identifier'] for item in google_identifier_values]
        for line in self:
            line.already_import = bool(line.album_identifier in google_identifier)

    def _prepare_gallery_values(self):
        return {
            'name': self.album_name,
            'google_identifier': self.album_identifier,
            'gallery_type': 'google',
            'google_last_sync_date': False,
            'website_id': self.wizard_id.website_id.id,
        }

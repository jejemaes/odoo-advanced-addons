# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, models, fields, _
from odoo.osv import expression
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import slug

from .google_api import GOOGLE_PHOTOS_BASE_URL_LIFETIME


class Gallery(models.Model):
    _inherit = 'website.gallery'

    google_identifier = fields.Char("Google Album Identifier")
    google_last_sync_date = fields.Datetime("Last Synchronization", readonly=True)
    gallery_type = fields.Selection(selection_add=[
        ('google', 'Google Photos API')
    ])

    _sql_constraints = [
        ('google_album_id_required', "CHECK((gallery_type='google' AND google_identifier IS NOT NULL) or (gallery_type != 'google'))", 'Google album needs a Google API identifier.'),
        ('website_id_required', "CHECK((gallery_type='google' AND website_id IS NOT NULL) or (gallery_type != 'google'))", 'Google album needs to be linked to a website, as public user of that website is used to fetch data.'),
    ]

    @api.constrains('image_per_page', 'gallery_type')
    def _check_image_per_page_google(self):
        for gallery in self:
            if gallery.image_per_page >= 50:
                raise ValidationError(_('Google Gallery can not contain more than 50 images per website page, for performance issue.'))

    def action_google_sync(self):
        return self._google_photo_sync()

    def _google_import_photos(self):
        """ Import all picture from google as website.gallery.image """
        result = {}
        for gallery in self.filtered(lambda gal: gal.gallery_type == 'google'):
            media_items = self.env['google.api'].sudo(gallery.website_id.user_id)._photos_fetch_all_media_items(gallery.google_identifier)
            images = self.env['google.api']._photos_create_gallery_image(gallery.id, media_items)
            result[gallery.id] = images

        self.filtered(lambda gal: gal.gallery_type == 'google').write({'google_last_sync_date': fields.Datetime.now()})

        return result

    def _google_photo_sync(self):
        """ Synchronize the new pictures from goole and remove the needed ones. This applies the state of google into Odoo """
        for gallery in self.filtered(lambda gal: gal.gallery_type == 'google'):
            media_items = self.env['google.api'].sudo(gallery.website_id.user_id)._photos_fetch_all_media_items(gallery.google_identifier)

            image_gid = gallery.image_ids.mapped('google_identifier')

            media_to_create = []
            media_ids_from_google = []
            image_gid_to_remove = []
            for media_item in media_items:
                if media_item['id'] not in image_gid:
                    media_to_create.append(media_item)
                media_ids_from_google.append(media_item['id'])

            # create the new image from google
            self.env['google.api'].sudo(gallery.website_id.user_id)._photos_create_gallery_image(gallery.id, media_to_create)

            # remove in odoo the ones removed from in google
            image_gid_to_remove = set(image_gid) - set(media_ids_from_google)
            self.search([('google_identifier', 'in', image_gid_to_remove)]).unlink()

        self.filtered(lambda gal: gal.gallery_type == 'google').write({'google_last_sync_date': fields.Datetime.now()})


class GalleryImage(models.Model):
    _inherit = 'website.gallery.image'

    google_identifier = fields.Char("Google Media Identifier", index=True)
    google_last_sync_date = fields.Datetime("Last Synchronization", readonly=True, help="Last update of baseUrl")
    google_url_expired = fields.Boolean("Google Base Url is still valid", compute='_compute_google_url_expired', search='_search_google_url_expired')

    @api.depends('gallery_id.gallery_type', 'attachment_id.type')
    def _compute_image_urls(self):
        super(GalleryImage, self)._compute_image_urls()
        for image in self:
            if image.gallery_type == 'google':
                if image.type == 'binary':
                    image.image_url = '/web/image/%s?unique=%s' % (image.attachment_id.id, image.attachment_id.checksum)
                    image.image_small_url = '/web/image/%s?height=250&unique=%s' % (image.attachment_id.id, image.attachment_id.checksum)
                    image.image_medium_url = '/web/image/%s?height=640&unique=%s' % (image.attachment_id.id, image.attachment_id.checksum)
                else:
                    image.image_url = '%s=h%s' % (image.attachment_id.url, 3200)
                    image.image_small_url = '%s=h%s' % (image.attachment_id.url, 250)
                    image.image_medium_url = '%s=h%s' % (image.attachment_id.url, 640)

    @api.depends('google_last_sync_date')
    def _compute_google_url_expired(self):
        for image in self:
            if image.google_last_sync_date:
                image.google_url_expired = image.google_last_sync_date + timedelta(minutes=GOOGLE_PHOTOS_BASE_URL_LIFETIME) < fields.Datetime.now()
            else:
                image.google_url_expired = True

    @api.model
    def _search_google_url_expired(self, operator, value):
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            value = not value
        expired_domain = [('google_last_sync_date', '<', fields.Datetime.now() - timedelta(minutes=GOOGLE_PHOTOS_BASE_URL_LIFETIME))]
        if value:
            return expired_domain
        return expression.distribute_not(expired_domain)

    def _google_update_url(self):
        """ Update the base url with a valid google url if needed. The url will be fetched and saved only if the url is expired. """
        expired_images = self.filtered(lambda img: img.google_url_expired)
        if not expired_images:
            return False

        websites = expired_images.mapped('gallery_id.website_id')
        grouped_by_website = dict.fromkeys(websites, self.env['website.gallery.image'])
        for image in expired_images:
            grouped_by_website[image.gallery_id.website_id] |= image

        for website, images in grouped_by_website.items():
            # fetch new google urls
            expired_images_gid = images.mapped('google_identifier')
            media_items = self.env['google.api'].sudo(website.user_id)._photos_batch_get_media_items(expired_images_gid)
            gid_url_map = {item['id']: item['baseUrl'] for item in media_items}

            # store them on the attachment
            for image in images.sudo():
                base_url = gid_url_map.get(image.google_identifier)
                if base_url:
                    image.write({
                        'url': base_url,
                        'google_last_sync_date': fields.Datetime.now(),
                    })
        return True

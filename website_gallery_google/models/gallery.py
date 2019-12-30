# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.addons.http_routing.models.ir_http import slug


class Gallery(models.Model):
    _inherit = 'website.gallery'

    google_identifier = fields.Char("Google Album Identifier")
    google_last_sync_date = fields.Datetime("Last Synchronization")
    gallery_type = fields.Selection(selection_add=[
        ('google', 'Google Photos API')
    ])

    _sql_constraints = [
        ('google_album_id_required', "CHECK((gallery_type='google' AND google_identifier IS NOT NULL) or (gallery_type != 'google'))", 'Google album needs a Google API identifier.'),
    ]

    def action_google_sync(self):
        return self._google_photo_sync()

    def _google_import_photos(self):
        """ Import all picture from google as website.gallery.image """
        result = {}
        for gallery in self.filtered(lambda gal: gal.gallery_type == 'google'):
            media_items = self.env['google.api']._photos_fetch_all_media_items(gallery.google_identifier)
            images = self.env['google.api']._photos_create_gallery_image(gallery.id, media_items)
            result[gallery.id] = images

        self.filtered(lambda gal: gal.gallery_type == 'google').write({'google_last_sync_date': fields.Datetime.now()})

        return result

    def _google_photo_sync(self):
        """ Synchronize the new pictures from goole and remove the needed ones. This applies the state of google into Odoo """
        for gallery in self.filtered(lambda gal: gal.gallery_type == 'google'):
            media_items = self.env['google.api']._photos_fetch_all_media_items(gallery.google_identifier)

            image_gid = gallery.image_ids.mapped('google_identifier')

            media_to_create = []
            media_ids_from_google = []
            image_gid_to_remove = []
            for media_item in media_items:
                if media_item['id'] not in image_gid:
                    media_to_create.append(media_item)
                media_ids_from_google.append(media_item['id'])

            # create the new image from google
            self.env['google.api']._photos_create_gallery_image(gallery.id, media_to_create)

            # remove in odoo the ones removed from in google
            image_gid_to_remove = set(image_gid) - set(media_ids_from_google)
            self.search([('google_identifier', 'in', image_gid_to_remove)]).unlink()

        self.filtered(lambda gal: gal.gallery_type == 'google').write({'google_last_sync_date': fields.Datetime.now()})


class GalleryImage(models.Model):
    _inherit = 'website.gallery.image'

    google_identifier = fields.Char("Google Media Identifier", index=True)

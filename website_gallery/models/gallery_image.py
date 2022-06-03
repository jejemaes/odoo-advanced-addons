# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.addons.http_routing.models.ir_http import slug


class GalleryImage(models.Model):
    _name = 'website.gallery.image'
    _description = 'Website Image Gallery'
    _inherit = ['website.published.mixin']
    _inherits = {'ir.attachment':'attachment_id'}
    _order = 'sequence ASC, id ASC'

    # attachment fields
    attachment_id = fields.Many2one('ir.attachment', 'File', domain=[('mimetype', 'ilike', 'image')], required=True, ondelete='cascade')
    public = fields.Boolean('Is public document', related='attachment_id.public', inherited=True, default=True, compute_sudo=True)  # public by default

    # website mixin
    is_published = fields.Boolean(default=True)

    # gallery image fields
    gallery_id = fields.Many2one('website.gallery', 'Gallery', required=True)
    gallery_type = fields.Selection(related='gallery_id.gallery_type', readonly=True)
    sequence = fields.Integer("Sequence", default=20)

    image_url = fields.Char("Image URL", compute='_compute_image_urls', compute_sudo=True)
    image_small_url = fields.Char("Thumbnail URL", compute='_compute_image_urls', compute_sudo=True)
    image_medium_url = fields.Char("Medium Image URL", compute='_compute_image_urls', compute_sudo=True)

    def _compute_display_name(self):
        for image in self.sudo():
            image.display_name = image.attachment_id.name

    def _compute_website_url(self):
        for image in self:
            image.website_url = '/gallery/%s/picture/%s' % (slug(image.gallery_id), slug(image))

    @api.depends('gallery_id.gallery_type', 'attachment_id.type')
    def _compute_image_urls(self):
        for image in self:
            if image.gallery_id.gallery_type:
                if image.type == 'binary':
                    image.image_url = '/web/image/%s?unique=%s' % (image.attachment_id.id, image.attachment_id.checksum)
                    image.image_small_url = '/web/image/%s?height=250&unique=%s' % (image.attachment_id.id, image.attachment_id.checksum)
                    image.image_medium_url = '/web/image/%s?height=640&unique=%s' % (image.attachment_id.id, image.attachment_id.checksum)
                else:
                    image.image_url = image.attachment_id.url
                    image.image_small_url = image.attachment_id.url
                    image.image_medium_url = image.attachment_id.url

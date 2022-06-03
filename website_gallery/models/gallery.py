# -*- coding: utf-8 -*-
import uuid

from odoo import api, models, fields
from odoo.addons.http_routing.models.ir_http import slug

DEFAULT_IMG_PER_PAGE = 20


class Gallery(models.Model):
    _name = 'website.gallery'
    _description = 'Website gallery'
    _inherit = ['website.seo.metadata', 'website.published.multi.mixin']

    name = fields.Char("Name", required=True)
    user_id = fields.Many2one('res.users', string="Author", default=lambda self: self.env.user.id)
    user_name = fields.Char(related="user_id.name", string="Author Name", related_sudo=True)
    date = fields.Date("Publication Date", default=fields.Date.today(), help="Displayed gallery date on website.")
    description = fields.Html("Description")
    tag_ids = fields.Many2many('website.gallery.tag', 'website_gallery_tag_rel', string='Tags')
    gallery_type = fields.Selection([
        ('manual', 'Manual')
    ], string="Gallery Type", default='manual', required=True, readonly=True, ondelete={'manual': 'cascade'})
    display_type = fields.Selection([
        ('page', 'Page'),
        ('modal', 'Modal')
    ], string="Display Type", default='modal', required=True, ondelete={'page': 'cascade', 'modal': 'cascade'})
    image_per_page = fields.Integer("Images per page", default=DEFAULT_IMG_PER_PAGE)

    image_id = fields.Many2one('website.gallery.image', "Cover Image", domain="[('gallery_id', '=', id)]")
    image_small_url = fields.Char("Thumbnail Cover Image URL", related='image_id.image_small_url')
    image_medium_url = fields.Char("Medium Cover Image URL", related='image_id.image_medium_url')
    image_url = fields.Char("Cover Image URL", related='image_id.image_url')

    image_ids = fields.One2many('website.gallery.image', 'gallery_id', "Images")
    image_count = fields.Integer("Number of Image", compute='_compute_image_count')

    def _compute_website_url(self):
        for gallery in self:
            gallery.website_url = '/gallery/%s' % (slug(gallery),)

    @api.depends('image_ids')
    def _compute_image_count(self):
        grouped_data = self.env['website.gallery.image'].read_group([('gallery_id', 'in', self.ids)], ['gallery_id'], ['gallery_id'])
        mapped_data = dict([(db['gallery_id'][0], db['gallery_id_count']) for db in grouped_data])
        for gallery in self:
            gallery.image_count = mapped_data.get(gallery.id, 0)


class GalleryTag(models.Model):
    _name = 'website.gallery.tag'
    _description = 'Website Gallery Tag'

    name = fields.Char("Name", required=True)
    color = fields.Integer("Color")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]

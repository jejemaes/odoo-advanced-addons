# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import werkzeug

from odoo import http, fields
from odoo.http import request
from odoo.osv import expression
from odoo.tools import html2plaintext

from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_gallery.models.gallery import DEFAULT_IMG_PER_PAGE


class WebsiteGallery(http.Controller):
    _gallery_per_page = 10

    @http.route([
        '/gallery',
        '/gallery/page/<int:page>',
    ], type='http', auth="public", website=True)
    def gallery_index(self, page=1, **post):
        domain = request.website.website_domain()
        Gallery = request.env['website.gallery']

        search_term = post.get('search_term')
        if search_term:
            domain = expression.AND([domain, [('name', 'ilike', search_term)]])

        total = Gallery.search_count(domain)
        pager = request.website.pager(
            url=request.httprequest.path.partition('/page/')[0],
            total=total,
            page=page,
            step=self._gallery_per_page,
        )
        galleries = Gallery.search(domain, offset=(page - 1) * self._gallery_per_page, limit=self._gallery_per_page)

        return request.render('website_gallery.gallery_index', {
            'galleries': galleries,
            'pager': pager,
            'search_term': search_term,
        })

    @http.route([
        '''/gallery/<model("website.gallery", "[('website_id', 'in', (False, current_website_id))]"):gallery>''',
        '''/gallery/<model("website.gallery"):gallery>/page/<int:page>''',
    ], type='http', auth="public", website=True)
    def gallery_page(self, gallery=None, page=1, **kwargs):
        """ Display the page with the pictures of the gallery, with pager, .... """
        if not gallery.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        domain = [('gallery_id', '=', gallery.id)]
        GalleryImage = request.env['website.gallery.image']
        image_per_page = gallery.image_per_page or DEFAULT_IMG_PER_PAGE

        # TODO JEM: not sure this is needed
        if request.env.user.has_group('website.group_website_designer'):
            domain = expression.AND([domain, ['|', ('website_published', '=', True), ('website_published', '=', False)]])

        images = GalleryImage.search(domain, offset=(page - 1) * image_per_page, limit=image_per_page)
        total = GalleryImage.search_count(domain)

        pager = request.website.pager(
            url=request.httprequest.path.partition('/page/')[0],
            total=total,
            page=page,
            step=image_per_page,
            url_args=kwargs,
        )

        return request.render('website_gallery.gallery_page', {
            'main_object': gallery,
            'gallery': gallery,
            'images': images,
            'pager': pager,
        })

    @http.route([
        '''/gallery/<model("website.gallery", "[('website_id', 'in', (False, current_website_id))]"):gallery>/picture/<model("website.gallery.image"):image>''',
    ], type='http', auth="public", website=True)
    def gallery_picture(self, gallery=None, image=None, **kwargs):
        if not gallery.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        return request.render('website_gallery.gallery_picture', {
            'main_object': image,
            'gallery': gallery,
            'image': image,
        })

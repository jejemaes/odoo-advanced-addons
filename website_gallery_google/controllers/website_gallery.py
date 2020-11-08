# -*- coding: utf-8 -*-

import werkzeug

from odoo import http
from odoo.http import request

from odoo.addons.website_gallery.controllers.main import WebsiteGallery


class WebsiteGalleryGoogle(WebsiteGallery):

    @http.route()
    def gallery_index(self, page=1, **kwargs):
        response = super(WebsiteGalleryGoogle, self).gallery_index(page=page, **kwargs)
        if response.is_qweb:
            galleries = response.qcontext.get('galleries')
            if galleries:
                cover_images = galleries.filtered(lambda gal: gal.gallery_type == 'google').mapped('image_id')
                cover_images._google_update_url()
        return response

    @http.route()
    def gallery_page(self, gallery=None, page=1, **kwargs):
        response = super(WebsiteGalleryGoogle, self).gallery_page(gallery=gallery, page=page, **kwargs)
        if response.is_qweb:
            if 'gallery' in response.qcontext and 'images' in response.qcontext:
                gallery = response.qcontext['gallery']
                images = response.qcontext['images']
                if gallery.gallery_type == 'google':
                    images._google_update_url()
        return response

    @http.route()
    def gallery_picture(self, gallery=None, image=None, **kwargs):
        response = super(WebsiteGalleryGoogle, self).gallery_picture(gallery=gallery, image=image, **kwargs)
        if response.is_qweb:
            if 'image' in response.qcontext:
                image = response.qcontext['image']
                if image.gallery_type == 'google':
                    image._google_update_url()
        return response

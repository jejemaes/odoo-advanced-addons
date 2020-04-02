# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.web_editor.controllers.main import Web_Editor


class Web_Editor(Web_Editor):

    @http.route('/website_blog/field/content', type='http', auth="user")
    def mass_mailing_FieldTextHtmlEmailTemplate(self, model=None, res_id=None, field=None, callback=None, **kwargs):
        kwargs['snippets'] = '/website/snippets'
        kwargs['template'] = 'website_blog_advanced.FieldTextHtmlInline'
        return self.FieldTextHtmlInline(model, res_id, field, callback, **kwargs)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Gallery from Google',
    'category': 'Extra Tools',
    'description': """
The module import photos for Google Photos API
===============================================
""",
    'depends': ['website_gallery', 'google'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/gallery_views.xml',
        'wizard/gallery_import_google_views.xml',
    ],
    'qweb': ['static/src/xml/gallery_import.xml'],

}

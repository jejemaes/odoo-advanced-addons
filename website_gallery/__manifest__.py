# -*- coding: utf-8 -*-

{
    'name': 'Website Gallery',
    'category': 'Website',
    'summary': 'Display picture on your website',
    'description': 'Display picture on your website',
    'version': '1.0',
    'depends': ['website'],
    'data': [
        'views/gallery_views.xml',
        'views/gallery_templates.xml',
        'security/ir.model.access.csv',
        'security/website_gallery_security.xml',
        'data/website_gallery_data.xml',
    ],
    'installable': False,
    'auto_install': False,
    'assets': {
        'web.assets_frontend': [
            'website_gallery/static/src/scss/website_gallery_grid.scss',
            'website_gallery/static/lib/jquery-magnific-popup/jquery.magnific-popup.min.js',
            # Modal Gallery
            'website_gallery/static/lib/lightbox2-2.11.1/css/lightbox.css',
            'website_gallery/static/lib/lightbox2-2.11.1/js/lightbox.js',
        ],
    }
}

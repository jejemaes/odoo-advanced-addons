# -*- coding: utf-8 -*-

{
    'name': 'Website Gallery',
    'category': 'Website',
    'summary': 'Display picture on your website',
    'description': 'Display picture on your website',
    'version': '1.0',
    'depends': ['website'],
    'data': [
        'views/assets.xml',
        'views/gallery_views.xml',
        'views/gallery_templates.xml',
        'security/ir.model.access.csv',
        'security/website_gallery_security.xml',
        'data/website_gallery_data.xml',
    ],
    'installable': True,
    'auto_install': False,
}

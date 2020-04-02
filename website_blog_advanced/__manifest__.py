# -*- coding: utf-8 -*-

{
    'name': 'Website Blog Advanced',
    'category': 'Website',
    'summary': 'Blog Team Writers',
    'description': 'Display picture on your website',
    'version': '1.0',
    'depends': ['website_blog'],
    'data': [
        'views/website_blog_views.xml',
        'views/website_blog_templates.xml',
        'security/website_blog_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}

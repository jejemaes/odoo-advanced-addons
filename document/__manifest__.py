# -*- coding: utf-8 -*-
{
    'name': "Document",
    'summary': "Document Management System",
    'description': """
        Upload, manage and share your Documents.
    """,
    'author': "jejemaes",
    'category': 'Extra Tools',
    'version': '1.0',
    'application': True,
    'depends': ['mail', 'portal', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/document_create_record_views.xml',
        'views/assets.xml',
        'views/res_config_settings_views.xml',
        'views/document_views.xml',
        'views/folder_views.xml',
        'views/share_views.xml',
        'views/tag_views.xml',
        'views/document_menus.xml',
        'views/document_share_templates.xml',
    ],
}

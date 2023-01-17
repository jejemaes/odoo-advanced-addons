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
        'wizard/document_attach_record_views.xml',
        'wizard/document_request_views.xml',
        'wizard/document_create_record_views.xml',
        'views/res_config_settings_views.xml',
        'views/document_views.xml',
        'views/folder_views.xml',
        'views/share_views.xml',
        'views/tag_views.xml',
        'views/document_menus.xml',
        'views/document_share_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'document/static/src/js/documents_kanban_record.js',
            'document/static/src/js/documents_kanban_renderer.js',
            'document/static/src/js/documents_kanban_controller.js',
            'document/static/src/js/documents_kanban_view.js',
            'document/static/src/scss/documents_kanban_view.scss',
        ],
        'web.assets_frontend': [
            'document/static/src/scss/document_frontent.scss',
        ],
        'web.assets_qweb': [
            'document/static/src/xml/document_kanban_controller.xml',
        ],
    }
}
